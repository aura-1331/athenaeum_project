import axios from 'axios'

export async function dispatchAuditTrail(
  actionType: string, 
  targetModule: string, 
  targetId: string | number | null, 
  description: string, 
  reason: string, 
  oldState: any = null, 
  newState: any = null
) {
  try {
    const sessionUser = localStorage.getItem('username') || localStorage.getItem('user') || 'UNKNOWN_ACTOR'
    const sessionRole = localStorage.getItem('user_role') || localStorage.getItem('role') || 'GUEST'
    const deviceSignature = 'EDITORIAL-STATION-01'
    const networkIp = '127.0.0.1'

    await axios.post('/status_audit/log', {
      actor_username: sessionUser,
      actor_role: sessionRole,
      action_type: actionType.toUpperCase(),
      target_module: targetModule.toUpperCase(),
      target_id: targetId ? String(targetId) : null,
      description: description,
      change_reason: reason,
      old_value: oldState,
      new_value: newState,
      device_id: deviceSignature,
      ip_address: networkIp
    })
  } catch (err) {
    console.error("Telemetry link lost. Local session action unlogged:", err)
  }
}