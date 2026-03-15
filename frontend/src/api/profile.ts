import apiClient from './client'
import type { Language, UserProfile, ProfileUpdate } from './types'

export async function getProfile(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>('/api/auth/profile')
  return response.data
}

export async function updateProfile(data: ProfileUpdate): Promise<UserProfile> {
  const response = await apiClient.post<UserProfile>('/api/auth/profile', data)
  return response.data
}

export async function getLanguages(): Promise<Language[]> {
  const response = await apiClient.get<Language[]>('/api/languages/')
  return response.data
}
