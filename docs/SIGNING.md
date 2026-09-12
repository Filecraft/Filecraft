# Maintainer signing guide

Filecraft 0.10.0-beta.1 has no Windows publisher signature or macOS Developer ID
notarization. The maintainer does not yet have signing keys configured. This is
setup guidance for a future release, not a certification or a record of completed
signing. Keep the current download warnings until the final artifacts are verified.

The owner must handle enrollment, identity checks, billing and legal agreements.
Do not buy a certificate or hardware token before checking eligibility and the
chosen provider's requirements. A personal hardware token is not universally
required: Azure Artifact Signing manages signing keys in its service HSMs.[6]

## macOS: Developer ID and notarization

1. Enroll in the Apple Developer Program. The Account Holder creates a Developer ID
   certificate through Xcode or the developer account. Use Developer ID Application
   for app code; a flat installer package needs the appropriate installer identity.[1][2]
2. Use a supported Xcode toolchain. Sign all distributed executables, including
   nested code, with valid Developer ID signatures. Enable Hardened Runtime for
   app and command-line targets and include secure timestamps.[2]
3. Review the entitlements needed by the packaged Python runtime and its libraries.
   Test the signed package's real GUI, CLI, rendering and optional-engine workflows.
   Do not assume the current unsigned packager already performs these steps.
4. Store notarization credentials in a local Keychain profile using `notarytool`.
   Submit the signed distribution and inspect its status and log. Apple accepts
   ZIP, DMG and flat installer packages; use `notarytool`, not retired `altool`.[3]
5. Require an `Accepted` result, then staple the ticket to the supported app or
   distribution container. For ZIP delivery, staple the app before creating the
   final ZIP. Test a fresh download through Gatekeeper before publication.[1][2][3]

Example submission after signing and local credential setup. Replace the sample
paths and profile name with the actual staged package and Keychain profile:

```sh
xcrun notarytool submit "staging/Filecraft.zip" --keychain-profile "filecraft-notary" --wait
xcrun notarytool log "SUBMISSION_ID" --keychain-profile "filecraft-notary" "notary-log.json"
```

For an app-bundle distribution, verify the actual bundle and its stapled ticket:

```sh
codesign --verify --deep --strict --verbose=2 "staging/Filecraft.app"
xcrun stapler staple "staging/Filecraft.app"
xcrun stapler validate "staging/Filecraft.app"
```

These are examples, not claims about the current package layout. A successful
upload is not an accepted notarization. Notarization is an automated malware and
code-signing check, not App Review or an independent security audit.[2]

## Windows: Azure Artifact Signing and SignTool

Check Public Trust eligibility before paying. Microsoft's current quickstart
limits individual developers to the United States and Canada; organizations have
a separate country list. An Azure subscription alone does not establish
eligibility. Private Trust is not a substitute for public distribution trust.[4]

1. Create an Artifact Signing account in an eligible Azure subscription, complete
   identity validation in the Azure portal and create a Public Trust certificate
   profile. Confirm the legal publisher name before submitting.[4]
2. Assign the signing identity the Artifact Signing Certificate Profile Signer
   role. Install the official Artifact Signing Client Tools on the Windows signing
   machine. Match the architectures of SignTool, the .NET runtime and the dlib.[5]
3. Create `metadata.json` with `Endpoint`, `CodeSigningAccountName` and
   `CertificateProfileName`. The endpoint must match the account's Azure region.
   Configure one intended authentication method rather than relying on an
   unexpected cached account.[5]
4. Sign the staged executable before making the release ZIP. Timestamp every
   signature: Artifact Signing certificates have a three-day validity, so the
   timestamp matters after the signing certificate expires.[5]

PowerShell example using the installed x64 tools and local metadata file:

```powershell
& "<SDK-bin>\x64\signtool.exe" sign /v /fd SHA256 /tr "http://timestamp.acs.microsoft.com" /td SHA256 /dlib "<client-bin>\x64\Azure.CodeSigning.Dlib.dll" /dmdf "<config>\metadata.json" "<staging>\Filecraft-Desktop.exe"
& "<SDK-bin>\x64\signtool.exe" verify /pa /all /v "<staging>\Filecraft-Desktop.exe"
```

The timestamp URL above is Microsoft's documented endpoint. SignTool checks
signature trust; it does not establish application safety or store approval.[5][7]
Record the verified publisher and timestamp, then repeat verification on the
executable extracted from the final downloaded ZIP. Do not promise that signing
will remove every Windows warning.

## Secrets and release records

- Never paste private keys, certificate export passwords, app-specific passwords,
  API keys or tokens into chat, issues, source files or build logs. Do not send
  identity documents to an agent; submit them directly to the provider.
- Keep local credentials in Keychain or an approved secret store. For CI, prefer
  short-lived federated or managed identity credentials where supported, limit
  signer access and require approval for release signing.
- Keep signing jobs separate from untrusted pull-request code. Review logs before
  sharing them; revoke or rotate exposed credentials immediately.
- Rebuild archives and calculate checksums after signing and stapling. Retain the
  source revision, tool versions, signing identity, notarization result and final
  artifact verification logs. Never replace historical release assets silently.
- Signing and notarization do not change Filecraft's document-processing limits,
  dependency licenses or unsigned receipt semantics. See [RELEASING.md](RELEASING.md).

## Sources

[1] https://developer.apple.com/developer-id
[2] https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
[3] https://developer.apple.com/documentation/security/customizing-the-notarization-workflow
[4] https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart
[5] https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations
[6] https://learn.microsoft.com/en-us/azure/artifact-signing/overview
[7] https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
