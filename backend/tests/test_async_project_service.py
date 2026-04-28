import pytest
from sqlalchemy import select

from models.project import MemberRole, ProjectMember
from models.user import User
from schemas.project import ProjectCreate, ProjectMemberCreate, ProjectUpdate


@pytest.fixture
def project_data():
    return ProjectCreate(name="Test Project", description="A test project description", members=[])


@pytest.mark.asyncio
async def test_create_project_success(
    async_project_service, test_user, project_data, async_session
):
    # Act
    project = await async_project_service.create_project(project_data, test_user.id)

    # Assert
    assert project.id is not None
    assert project.name == project_data.name
    assert project.description == project_data.description
    assert project.owner_id == test_user.id

    # Verify owner member created
    stmt = select(ProjectMember).filter_by(project_id=project.id, user_id=test_user.id)
    result = await async_session.execute(stmt)
    member = result.scalars().first()
    assert member is not None
    assert member.role == MemberRole.OWNER.value


@pytest.mark.asyncio
async def test_create_project_limit_check(
    async_project_service, test_user, project_data, async_session
):
    # Setup - mock subscription limit
    # Default is FREE which has 2 projects.
    # Let's create 2 projects first
    await async_project_service.create_project(ProjectCreate(name="P1"), test_user.id)
    await async_project_service.create_project(ProjectCreate(name="P2"), test_user.id)

    # Act & Assert - Try to create 3rd
    with pytest.raises(ValueError, match="Project limit reached"):
        await async_project_service.create_project(ProjectCreate(name="P3"), test_user.id)


@pytest.mark.asyncio
async def test_create_project_with_members(async_project_service, test_user, async_session):
    # Create another user to be a member
    other_user = User(
        email="other@test.com", name="Other User", hashed_password="pw", is_active=True
    )
    async_session.add(other_user)
    await async_session.commit()
    await async_session.refresh(other_user)

    # Project with member
    p_data = ProjectCreate(
        name="Team Project",
        members=[ProjectMemberCreate(user_id=str(other_user.id), role="member")],
    )

    project = await async_project_service.create_project(p_data, test_user.id)

    # Verify member added
    stmt = select(ProjectMember).filter_by(project_id=project.id, user_id=other_user.id)
    result = await async_session.execute(stmt)
    member = result.scalars().first()
    assert member is not None
    assert member.role == "member"


@pytest.mark.asyncio
async def test_get_project_by_id(async_project_service, test_user, project_data):
    created = await async_project_service.create_project(project_data, test_user.id)
    fetched = await async_project_service.get_project_by_id(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_update_project(async_project_service, test_user, project_data):
    project = await async_project_service.create_project(project_data, test_user.id)

    update_data = ProjectUpdate(name="Updated Name", description="Updated Desc")
    updated = await async_project_service.update_project(project.id, update_data, test_user.id)

    assert updated.name == "Updated Name"
    assert updated.description == "Updated Desc"


@pytest.mark.asyncio
async def test_update_project_not_owner(
    async_project_service, test_user, project_data, async_session
):
    project = await async_project_service.create_project(project_data, test_user.id)

    other_user = User(email="o@t.com", name="O", hashed_password="p", is_active=True)
    async_session.add(other_user)
    await async_session.commit()
    await async_session.refresh(other_user)

    with pytest.raises(ValueError, match="Only project owners and admins"):
        await async_project_service.update_project(
            project.id, ProjectUpdate(name="New"), other_user.id
        )


@pytest.mark.asyncio
async def test_delete_project(async_project_service, test_user, project_data, async_session):
    project = await async_project_service.create_project(project_data, test_user.id)

    success = await async_project_service.delete_project(project.id, test_user.id)
    assert success is True

    # Verify gone
    fetched = await async_project_service.get_project_by_id(project.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_add_project_member(async_project_service, test_user, project_data, async_session):
    project = await async_project_service.create_project(project_data, test_user.id)

    other_user = User(email="m@t.com", name="M", hashed_password="p", is_active=True)
    async_session.add(other_user)
    await async_session.commit()
    await async_session.refresh(other_user)

    member = await async_project_service.add_project_member(
        project.id, ProjectMemberCreate(user_id=str(other_user.id), role="admin"), test_user.id
    )

    assert member.user_id == other_user.id
    assert member.role == MemberRole.ADMIN.value


@pytest.mark.asyncio
async def test_remove_project_member(async_project_service, test_user, project_data, async_session):
    project = await async_project_service.create_project(project_data, test_user.id)

    other_user = User(email="rm@t.com", name="RM", hashed_password="p", is_active=True)
    async_session.add(other_user)
    await async_session.commit()
    await async_session.refresh(other_user)

    await async_project_service.add_project_member(
        project.id, ProjectMemberCreate(user_id=str(other_user.id), role="member"), test_user.id
    )

    success = await async_project_service.remove_project_member(
        project.id, other_user.id, test_user.id
    )
    assert success is True

    # Verify removed
    stmt = select(ProjectMember).filter_by(project_id=project.id, user_id=other_user.id)
    res = await async_session.execute(stmt)
    assert res.scalars().first() is None


@pytest.mark.asyncio
async def test_get_projects_with_stats(async_project_service, test_user, project_data):
    await async_project_service.create_project(project_data, test_user.id)

    stats = await async_project_service.get_projects_with_stats(user_id=test_user.id)
    assert len(stats) == 1
    s = stats[0]
    assert s["project"].name == project_data.name
    assert "task_count" in s
    assert "completed_tasks" in s


@pytest.mark.asyncio
async def test_add_project_members_bulk(
    async_project_service, test_user, project_data, async_session
):
    project = await async_project_service.create_project(project_data, test_user.id)

    u1 = User(email="u1@t.com", name="U1", hashed_password="p", is_active=True)
    u2 = User(email="u2@t.com", name="U2", hashed_password="p", is_active=True)
    async_session.add_all([u1, u2])
    await async_session.commit()
    await async_session.refresh(u1)
    await async_session.refresh(u2)

    members_data = [
        ProjectMemberCreate(user_id=str(u1.id), role="member"),
        ProjectMemberCreate(user_id=str(u2.id), role="member"),
    ]

    result = await async_project_service.add_project_members_bulk(
        project.id, members_data, test_user.id
    )

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_project_with_details(async_project_service, test_user, project_data):
    project = await async_project_service.create_project(project_data, test_user.id)

    details = await async_project_service.get_project_with_details(project.id)
    assert details is not None
    assert details["project"].id == project.id
    assert details["member_count"] >= 1  # Owner


@pytest.mark.asyncio
async def test_check_member_limit(async_project_service, test_user, async_session):
    # Mock limits to be low
    # We can override _get_user_plan_limits by mocking or just creating enough members
    # Free plan has 3 members

    # Default is Free.
    # Create project
    p = await async_project_service.create_project(ProjectCreate(name="LimitP"), test_user.id)

    # We already have 1 member (owner). Need 3 more to fail (limit is 3 total? or additional?)
    # "members": 3. Limit includes owner? Usually yes, code says:
    # current_count = 1 (Owner)
    # create_project checks "current_count + new_count <= max_members"

    u1 = User(email="m1@t.com", name="M1", hashed_password="p", is_active=True)
    u2 = User(email="m2@t.com", name="M2", hashed_password="p", is_active=True)
    u3 = User(email="m3@t.com", name="M3", hashed_password="p", is_active=True)
    async_session.add_all([u1, u2, u3])
    await async_session.commit()
    await async_session.refresh(u1)
    await async_session.refresh(u2)
    await async_session.refresh(u3)

    # Add 2 members -> Total 3. OK.
    await async_project_service.add_project_member(
        p.id, ProjectMemberCreate(user_id=str(u1.id), role="member"), test_user.id
    )
    await async_project_service.add_project_member(
        p.id, ProjectMemberCreate(user_id=str(u2.id), role="member"), test_user.id
    )

    # Add 3rd member -> Total 4. Should Fail.
    with pytest.raises(ValueError, match="Team member limit reached"):
        await async_project_service.add_project_member(
            p.id, ProjectMemberCreate(user_id=str(u3.id), role="member"), test_user.id
        )


@pytest.mark.asyncio
async def test_update_member_role(async_project_service, test_user, project_data, async_session):
    project = await async_project_service.create_project(project_data, test_user.id)

    u = User(email="role@t.com", name="R", hashed_password="p", is_active=True)
    async_session.add(u)
    await async_session.commit()
    await async_session.refresh(u)

    await async_project_service.add_project_member(
        project.id, ProjectMemberCreate(user_id=str(u.id), role="member"), test_user.id
    )

    updated = await async_project_service.update_member_role(
        project.id, u.id, "admin", test_user.id
    )
    assert updated.role == MemberRole.ADMIN.value
