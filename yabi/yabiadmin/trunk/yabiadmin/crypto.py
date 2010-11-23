# -*- coding: utf-8 -*-
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
import base64
import math
import binascii

#
# this is a chunking lambda generator
#
chunkify = lambda v, l: (v[i*l:(i+1)*l] for i in range(int(math.ceil(len(v)/float(l)))))

#
# Some exceptions to notify callers of failure to decrypt if validity is being checked (not just blind decrypt)
#
class DecryptException(Exception): pass

def aes_enc(data,key):
    if not data:
        return data                         # encrypt nothing. get nothing.
        
    assert data[-1]!='\0', "encrypt/decrypt implementation uses null padding and cant reliably decrypt a binary string that ends in \\0"
    #
    # Our AES Cipher
    #
    key_hash = SHA256.new(key)
    aes = AES.new(key_hash.digest())
    
    # pad to nearest 16.
    data += '\0'*(16-(len(data)%16))
    
    # take chunks of 16
    output = ""
    for chunk in chunkify(data,16):
        output += aes.encrypt(chunk)
        
    return output
    
def aes_enc_base64(data,key,linelength=None):
    """DO an aes encrypt, but return data as base64 encoded"""
    enc = aes_enc(data,key)
    encoded = base64.encodestring(enc)
    
    if linelength:
        encoded = "\n".join(chunkify(encoded,linelength))
    
    return encoded

def aes_enc_hex(data,key,linelength=None):
    """DO an aes encrypt, but return data as base64 encoded"""
    enc = aes_enc(data,key)
    encoded = binascii.hexlify(enc)
    
    if linelength:
        encoded = "\n".join(chunkify(encoded,linelength))
    
    return encoded
      
def aes_dec(data,key, check=False):
    if not data:
        return data                     # decrypt nothing, get nothing
    
    key_hash = SHA256.new(key)
    aes = AES.new(key_hash.digest())
    
    # take chunks of 16
    output = ""
    for chunk in chunkify(data,16):
        output += aes.decrypt(chunk)
        
    # depad the plaintext
    while output.endswith('\0'):
        output = output[:-1]
    
    if contains_binary(output):
        raise DecryptException, "AES decrypt failed. Decrypted data contains binary"
    
    return output
    
def aes_dec_base64(data,key, check=False):
    """decrypt a base64 encoded encrypted block"""
    ciphertext = base64.decodestring("".join(data.split("\n")))
    return aes_dec(ciphertext, key, check)

def aes_dec_hex(data,key, check=False):
    """decrypt a base64 encoded encrypted block"""
    ciphertext = binascii.unhexlify("".join("".join(data.split("\n")).split("\r")))
    return aes_dec(ciphertext, key, check)
    
def contains_binary(data):
    """return true if string 'data' contains any binary"""
    # for now just see if there are any unprintable characters in the string
    import string
    return False in [X in string.printable for X in data]