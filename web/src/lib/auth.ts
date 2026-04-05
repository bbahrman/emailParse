import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from "amazon-cognito-identity-js";

let _userPool: CognitoUserPool | null = null;

function getUserPool(): CognitoUserPool {
  if (!_userPool) {
    const poolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
    const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
    if (!poolId || !clientId) {
      throw new Error("Cognito not configured. Set NEXT_PUBLIC_COGNITO_USER_POOL_ID and NEXT_PUBLIC_COGNITO_CLIENT_ID.");
    }
    _userPool = new CognitoUserPool({ UserPoolId: poolId, ClientId: clientId });
  }
  return _userPool;
}

export function signIn(
  email: string,
  password: string
): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getUserPool() });
    const authDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    user.authenticateUser(authDetails, {
      onSuccess: (session) => resolve(session),
      onFailure: (err) => reject(err),
      newPasswordRequired: (_userAttributes) => {
        // For first login after admin-create-user, set the permanent password
        // This shouldn't happen in normal flow since we use admin-set-user-password
        reject(new Error("New password required. Please contact the admin."));
      },
    });
  });
}

export function getSession(): Promise<CognitoUserSession | null> {
  return new Promise((resolve) => {
    let user;
    try {
      user = getUserPool().getCurrentUser();
    } catch {
      resolve(null);
      return;
    }
    if (!user) {
      resolve(null);
      return;
    }
    user.getSession(
      (err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session || !session.isValid()) {
          resolve(null);
          return;
        }
        resolve(session);
      }
    );
  });
}

export function getIdToken(): Promise<string | null> {
  return getSession().then((session) =>
    session ? session.getIdToken().getJwtToken() : null
  );
}

export function signOut(): void {
  try {
    const user = getUserPool().getCurrentUser();
    if (user) {
      user.signOut();
    }
  } catch {
    // Cognito not configured
  }
}
