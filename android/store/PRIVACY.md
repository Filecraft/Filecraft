# Prepare for Android — privacy foundation

Experimental, not yet store-published. Prepare has no INTERNET permission,
telemetry, ads, analytics SDKs, account, server, or runtime third-party libraries.
Images are processed on device. Only JPEG/PNG files selected through Android's
Storage Access Framework are read. Choose local device storage: a system document
provider is a separate app and may sync files independently; LOCAL_ONLY is requested.

Conversion rasterizes images onto white PDF pages. Embedded source EXIF/GPS and
text metadata are not copied; orientation is applied. Visible personal content is
not redacted. PDFs may contain metadata emitted by Android's native PDF writer.
No claim of forensic sanitization, secure erasure, lossless conversion or OCR.

Prepared PDFs live in private cache until clear, recreation/exit cleanup, OS cache
reclamation, or next startup. An abrupt process death may leave private temporary
files until the next startup. App backup and device-transfer data are excluded.
Clearing the workspace does not delete originals or user-saved copies. A new copy
is saved only to a user-selected system destination; save is read-back verified.
A provider error/cancellation may leave a partial destination if deletion fails.

No data is sent to the developer. Contact/security reporting:
https://github.com/gonisulaimann/Prepare/security

Before a store submission: host this policy at a stable public HTTPS URL, confirm
contact details and review actual platform/OEM behavior. This file is a foundation,
not an assertion of store approval or a completed legal review.
