"""One-off check that Entra sign-in + the Graph profile lookup work.

Run:  python try_signin.py

It prints a short code and a URL. Open the URL in any browser, enter the code,
sign in with your Microsoft work account, and this script prints your profile.
That proves the whole auth path works on its own, before we wire it into the
main app. Once it works, this file can be deleted (or kept as a smoke test).
"""

from helpdesk.auth.entra_auth import EntraAuth


def main():
    auth = EntraAuth()

    if not auth.configured:
        print(
            "Entra is not configured. Check that AZURE_AUTH_CLIENT_ID and "
            "AZURE_AUTH_TENANT_ID are set in your .env."
        )
        return

    print("Starting Microsoft sign-in (device code flow)...")
    profile = auth.sign_in()

    if profile is None:
        print("Sign-in did not complete. See the message above for the reason.")
        return

    print("\nSigned in successfully. Your profile from Microsoft Graph:")
    print(f"  Name:       {profile.name}")
    print(f"  Email:      {profile.email}")
    print(f"  Job title:  {profile.job_title or '(not set)'}")
    print(f"  Department: {profile.department or '(not set)'}")


if __name__ == "__main__":
    main()
