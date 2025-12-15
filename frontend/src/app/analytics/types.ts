// define types for analytics data if they are not imported
export interface AnalyticsTrend {
  metric: string;
  current: number;
  previous: number;
  change: number;
  trend: "up" | "down";
}

export interface AnalyticsProject {
  id: string;
  name: string;
  tasks: number;
  completed: number;
  progress: number;
  velocity: "high" | "medium" | "low";
}

export interface AnalyticsTeamMember {
  name: string;
  avatar?: string;
  tasks: number;
  completed: number;
  efficiency: number;
}

export interface AnalyticsOverview {
  totalProjects: number;
  activeProjects: number;
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  overdueTasks: number;
  teamMembers: number;
  completionRate: number;
  averageCompletionTime: number;
  teamVelocity: number;
}

export interface BurndownDataPoint {
  day: string;
  planned: number;
  actual: number;
}

export interface AnalyticsResponse {
  overview: AnalyticsOverview;
  trends: AnalyticsTrend[];
  projects: AnalyticsProject[];
  team: AnalyticsTeamMember[];
  weeklyBurndown: BurndownDataPoint[];
  statusDistribution: { name: string; value: number }[];
  priorityDistribution: { name: string; value: number }[];
  teamWorkload: { name: string; avatar?: string; tasks: number }[];
  dailyTrends: { date: string; created: number; completed: number }[];
}

// Types for paginated team workload (scalable for 1K-100K users)
export interface TeamWorkloadItem {
  name: string;
  avatar?: string;
  tasks: number;
}

export interface TeamWorkloadPaginatedResponse {
  items: TeamWorkloadItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface TeamWorkloadParams {
  page?: number;
  pageSize?: number;
  search?: string;
  sortBy?: "tasks" | "name";
  sortOrder?: "asc" | "desc";
}
