import apiClient from './client'
import type { DashboardStats } from './types'

export async function getDashboardStats(
  languageId: string,
): Promise<DashboardStats> {
  const response = await apiClient.get<DashboardStats>(
    `/api/dashboard/${languageId}`,
  )
  return response.data
}
