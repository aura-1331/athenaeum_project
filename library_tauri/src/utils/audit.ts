/**
 * Legacy client audit hook.
 *
 * Security-sensitive audit records are created by the authenticated backend
 * route that performs the mutation. This helper intentionally performs no
 * network request because there is no client-authoritative audit endpoint.
 */
export async function dispatchAuditTrail(
  _actionType: string,
  _targetModule: string,
  _targetId: string | number | null,
  _description: string,
  _reason: string,
  _oldState: any = null,
  _newState: any = null
) {
  return
}
