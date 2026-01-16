import pytest
import uuid
from sqlalchemy import select
from models.project import Project, ProjectMember, MemberRole
from models.user import User
from services.async_usage_service import AsyncUsageService
from utils.auth import get_password_hash

# We use the existing fixtures from conftest.py
# async_session, test_user are available

@pytest.mark.asyncio
async def test_get_user_usage_stats_empty(async_session, test_user):
    """Test usage stats for a user with no projects."""
    service = AsyncUsageService(async_session)
    stats = await service.get_user_usage_stats(test_user)
    
    assert stats["projects_used"] == 0
    # Even with 0 projects, logic defaults seats to 1 (the user themselves) if count is 0
    assert stats["seats_used"] == 1 

@pytest.mark.asyncio
async def test_get_user_usage_stats_owner_only(async_session, test_user):
    """Test usage stats for a user owning projects but no other members."""
    # Create 2 projects owned by test_user
    p1 = Project(name="P1", owner_id=test_user.id)
    p2 = Project(name="P2", owner_id=test_user.id)
    async_session.add_all([p1, p2])
    await async_session.commit()
    await async_session.refresh(p1)
    await async_session.refresh(p2)
    
    # Add owner as member (business logic usually does this, though service query relies on ProjectMember OR Owner check)
    # The service query:
    # Projects Count: outerjoin ProjectMember where Owner OR Member
    # Seats Count: distinct ProjectMember.user_id where project_id in MyProjects
    
    # If we don't add ProjectMember for owner, seats count query might return 0 (logic handles 0->1)
    # Let's add ProjectMember for owner to simulate real app behavior
    pm1 = ProjectMember(project_id=p1.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    pm2 = ProjectMember(project_id=p2.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    async_session.add_all([pm1, pm2])
    await async_session.commit()

    service = AsyncUsageService(async_session)
    stats = await service.get_user_usage_stats(test_user)
    
    assert stats["projects_used"] == 2
    assert stats["seats_used"] == 1  # Only myself

@pytest.mark.asyncio
async def test_get_user_usage_stats_with_team(async_session, test_user):
    """Test usage stats with team members in owned projects."""
    # Create a project
    p1 = Project(name="Team Project", owner_id=test_user.id)
    async_session.add(p1)
    await async_session.commit()
    await async_session.refresh(p1)
    
    # Create another user
    other_user = User(
        email="other@example.com", 
        hashed_password=get_password_hash("pw"), 
        name="Other",
        is_active=True
    )
    async_session.add(other_user)
    await async_session.commit()
    await async_session.refresh(other_user)
    
    # Add both as members
    pm1 = ProjectMember(project_id=p1.id, user_id=test_user.id, role=MemberRole.OWNER.value)
    pm2 = ProjectMember(project_id=p1.id, user_id=other_user.id, role=MemberRole.MEMBER.value)
    async_session.add_all([pm1, pm2])
    await async_session.commit()
    
    service = AsyncUsageService(async_session)
    stats = await service.get_user_usage_stats(test_user)
    
    assert stats["projects_used"] == 1
    assert stats["seats_used"] == 2 # Me + Other

@pytest.mark.asyncio
async def test_get_user_usage_stats_as_member_only(async_session, test_user):
    """Test usage stats when user is just a member of someone else's project."""
    # Create another user who owns the project
    owner = User(
        email="boss@example.com", 
        hashed_password=get_password_hash("pw"), 
        name="Boss",
        is_active=True
    )
    async_session.add(owner)
    await async_session.commit()
    await async_session.refresh(owner)
    
    p1 = Project(name="Boss Project", owner_id=owner.id)
    async_session.add(p1)
    await async_session.commit()
    await async_session.refresh(p1)
    
    # Join test_user as member
    pm1 = ProjectMember(project_id=p1.id, user_id=test_user.id, role=MemberRole.MEMBER.value)
    async_session.add(pm1)
    await async_session.commit()
    
    service = AsyncUsageService(async_session)
    stats = await service.get_user_usage_stats(test_user)
    
    # Projects used should count this project
    assert stats["projects_used"] == 1
    
    # Seats used counts distinct members in *MY* owned projects.
    # I own 0 projects, so seats should be 0 -> defaults to 1.
    assert stats["seats_used"] == 1
