import apiClient from './client'
import type { DashboardStats } from './types'

export async function getDashboardStats(
  languageId: string,
): Promise<DashboardStats> {
  // The browser's timezone makes the daily-goal counter and streak roll
  // over at the learner's local midnight (UTC midnight lands mid-evening
  // for US users). Invalid/missing zones degrade to UTC server-side.
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  const response = await apiClient.get<DashboardStats>(
    `/api/dashboard/${languageId}`,
    { params: { tz } },
  )
  return response.data
}
