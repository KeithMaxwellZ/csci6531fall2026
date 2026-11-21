# 6. Known Limitations and Future Work

## Known Limitations

The largest limitation is that the network connection currently uses HTTP instead of TLS. The message contents are encrypted before they leave the client, but an attacker monitoring the network could still see or change credentials, session tokens, 2FA requests, routing information, and other metadata. A malicious router could also block messages, replay requests, or make the service unavailable. For that reason, the current deployment should not be used over an untrusted network.

The key-continuity feature has limitations as well. The application can detect that a contact's public key changed, but it does not yet include a complete out-of-band verification process, key rotation and revocation workflow, or secure key backup and recovery. If a private key is lost, the user may lose access to messages. If it is stolen, an attacker could impersonate the user until the key is revoked.


## Future Work

The first improvement would be to replace HTTP with TLS. This would protect login information, session tokens, 2FA requests, and other data while it travels between the client, router, and server. We would also make sure that sensitive information is not written to logs.

The second improvement would be to improve key management. The application should give users a clear way to verify a contact's public key and warn them when that key changes. It should also support key rotation, key revocation, and recovery when a device or private key is lost.


