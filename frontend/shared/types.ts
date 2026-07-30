export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ThreatUpdatePayload {
  type: string;
  session_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  fast_path_alert: boolean;
  latest_transcript: string;
  detected_tactics: string[];
  explanation: string;
  recommended_action: string;
}

export interface SessionConfig {
  user_id: string;
  device_type: string;
}
