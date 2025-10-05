"""
ARIA SDK - Telemetry Cryptography Module

Provides sign-then-encrypt using NaCl (Ed25519 + ChaCha20-Poly1305).
"""

from typing import Optional
import nacl.secret
import nacl.signing
import nacl.encoding
import nacl.utils

from aria_sdk.domain.protocols import ICryptoBox


class CryptoBox(ICryptoBox):
    """
    NaCl-based cryptography: Ed25519 signatures + ChaCha20-Poly1305 encryption.
    
    Security model: Sign-then-encrypt
    1. Sign payload with Ed25519 (authentication)
    2. Encrypt (payload || signature) with ChaCha20-Poly1305 (confidentiality)
    """
    
    def __init__(self, signing_key: Optional[bytes] = None, encryption_key: Optional[bytes] = None):
        """
        Initialize crypto box.
        
        Args:
            signing_key: 32-byte Ed25519 signing key (generates new if None)
            encryption_key: 32-byte ChaCha20 key (generates new if None)
        """
        if signing_key is not None:
            if len(signing_key) != 32:
                raise ValueError(f"Signing key must be 32 bytes, got {len(signing_key)}")
            self.signing_key = nacl.signing.SigningKey(signing_key)
        else:
            self.signing_key = nacl.signing.SigningKey.generate()
        
        if encryption_key is not None:
            if len(encryption_key) != 32:
                raise ValueError(f"Encryption key must be 32 bytes, got {len(encryption_key)}")
            self.encryption_box = nacl.secret.SecretBox(encryption_key)
        else:
            self.encryption_box = nacl.secret.SecretBox(nacl.utils.random(32))
        
        # Public verify key for others to verify our signatures
        self.verify_key = self.signing_key.verify_key
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Sign and encrypt data.
        
        Args:
            plaintext: Data to protect
            
        Returns:
            Encrypted bytes (includes signature and nonce)
        """
        # 1. Sign the plaintext
        signed_message = self.signing_key.sign(plaintext)
        # signed_message contains: signature (64 bytes) + plaintext
        
        # 2. Encrypt signed message
        # SecretBox.encrypt() automatically adds 24-byte nonce
        encrypted = self.encryption_box.encrypt(signed_message)
        
        return encrypted
    
    def decrypt(self, ciphertext: bytes, verify_key: Optional[bytes] = None) -> bytes:
        """
        Decrypt and verify data.
        
        Args:
            ciphertext: Encrypted data
            verify_key: 32-byte Ed25519 verify key (uses own if None)
            
        Returns:
            Original plaintext
            
        Raises:
            ValueError: If decryption or verification fails
        """
        try:
            # 1. Decrypt
            signed_message = self.encryption_box.decrypt(ciphertext)
            
            # 2. Verify signature
            if verify_key is not None:
                verifier = nacl.signing.VerifyKey(verify_key)
            else:
                verifier = self.verify_key
            
            # Verify and extract original plaintext
            plaintext = verifier.verify(signed_message)
            
            return plaintext
            
        except nacl.exceptions.CryptoError as e:
            raise ValueError(f"Decryption/verification failed: {e}") from e
    
    def get_public_keys(self) -> tuple[bytes, bytes]:
        """
        Get public keys for sharing.
        
        Returns:
            Tuple of (verify_key_32bytes, encryption_key_32bytes)
            Note: For symmetric encryption, we return same key (not ideal for production)
        """
        verify_key_bytes = bytes(self.verify_key)
        # For symmetric SecretBox, there's no public key, but we return the key itself
        # In production, use asymmetric encryption (NaCl Box) instead
        encryption_key_bytes = bytes(self.encryption_box._key)
        return (verify_key_bytes, encryption_key_bytes)
    
    @staticmethod
    def generate_keys() -> tuple[bytes, bytes]:
        """
        Generate new key pair.
        
        Returns:
            Tuple of (signing_key_32bytes, encryption_key_32bytes)
        """
        signing_key = nacl.signing.SigningKey.generate()
        encryption_key = nacl.utils.random(32)
        return (bytes(signing_key), encryption_key)


class AsymmetricCryptoBox(ICryptoBox):
    """
    Asymmetric NaCl crypto: Ed25519 + X25519 (Curve25519).
    
    Better for multi-party communication where each party has public/private keys.
    """
    
    def __init__(
        self,
        signing_key: Optional[bytes] = None,
        private_key: Optional[bytes] = None,
        peer_public_key: Optional[bytes] = None
    ):
        """
        Initialize asymmetric crypto.
        
        Args:
            signing_key: Ed25519 signing private key
            private_key: X25519 private key for encryption
            peer_public_key: Peer's X25519 public key (needed for encryption)
        """
        import nacl.public
        
        # Signing key
        if signing_key:
            self.signing_key = nacl.signing.SigningKey(signing_key)
        else:
            self.signing_key = nacl.signing.SigningKey.generate()
        
        self.verify_key = self.signing_key.verify_key
        
        # Encryption keys
        if private_key:
            self.private_key = nacl.public.PrivateKey(private_key)
        else:
            self.private_key = nacl.public.PrivateKey.generate()
        
        self.public_key = self.private_key.public_key
        
        # Peer's public key (needed for Box construction)
        self.peer_public_key = nacl.public.PublicKey(peer_public_key) if peer_public_key else None
        self.box = nacl.public.Box(self.private_key, self.peer_public_key) if peer_public_key else None
    
    def set_peer_public_key(self, peer_public_key: bytes):
        """Set peer's public key for encryption."""
        import nacl.public
        self.peer_public_key = nacl.public.PublicKey(peer_public_key)
        self.box = nacl.public.Box(self.private_key, self.peer_public_key)
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Sign and encrypt for peer."""
        if not self.box:
            raise RuntimeError("Peer public key not set - call set_peer_public_key() first")
        
        # Sign
        signed_message = self.signing_key.sign(plaintext)
        
        # Encrypt
        encrypted = self.box.encrypt(signed_message)
        
        return encrypted
    
    def decrypt(self, ciphertext: bytes, verify_key: Optional[bytes] = None) -> bytes:
        """Decrypt from peer and verify."""
        if not self.box:
            raise RuntimeError("Peer public key not set")
        
        try:
            # Decrypt
            signed_message = self.box.decrypt(ciphertext)
            
            # Verify
            if verify_key:
                verifier = nacl.signing.VerifyKey(verify_key)
            else:
                verifier = self.verify_key
            
            plaintext = verifier.verify(signed_message)
            return plaintext
            
        except Exception as e:
            raise ValueError(f"Asymmetric decryption failed: {e}") from e
    
    def get_public_keys(self) -> tuple[bytes, bytes]:
        """Get public keys to share with peers."""
        return (bytes(self.verify_key), bytes(self.public_key))
