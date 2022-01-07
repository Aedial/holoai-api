# Port of the tssrp6a library used for authentification
# Kudos to Schmitty#5079 for doing a rough translation from Javascript to Python
# of the important functions

import hashlib
import secrets

from typing import Tuple, List, Iterable

N = 21766174458617435773191008891802753781907668374255538511144643224689886235383840957210909013086056401571399717235807266581649606472148410291413364152197364477180887395655483738115072677402235101762521901569820740293149529620419333266262073471054548368736039519702486226506248861060256971802984953561121442680157668000761429988222457090413873973970171927093992114751765168063614761119615476233422096442783117971236371647333871414335895773474667308967050807005509320424799678417036867928316761272274230314067548291133582479583061439577559347101961771406173684378522703483495337037655006751328447510550299250924469288819

SALT_LEN = 128
PRIVATE_VALUE_LEN = 256

NG = 2048
NG_BYTES = (NG + 7) // 8

def btoi(b: bytes) -> int:
    return int.from_bytes(b, 'big', signed = False)

def itob(i: int) -> bytes:
    length = (i.bit_length() + 7) // 8

    return i.to_bytes(length, 'big', signed = False)

def pad_bytes(b: bytes, length: int) -> bytes:
    return b.rjust(length, b'\x00')

def hash(*args: List[bytes]) -> bytes:
    h = hashlib.sha512()

    for b in args:
        h.update(b)

    return h.digest()

def hash_padded(*args: List[bytes]) -> bytes:
    return hash(*(pad_bytes(a, NG_BYTES) for a in args))

def compute_identity_hash(P: str) -> bytes:
    return hash(P.encode())

def compute_x(s: int, P: str) -> int:
    return btoi(hash(itob(s), compute_identity_hash(P)))

def random_bytes(length: int) -> int:
    return btoi(secrets.token_bytes(length))

def create_verifier(s: int, P: str) -> int:
    x = compute_x(s, P)

    return pow(2, x, N)

def create_verifier_and_salt(P: str) -> Tuple[int, int]:
    s = random_bytes(SALT_LEN)
    v = create_verifier(s, P)

    return (s, v)

def generate_private_value() -> int:
    pv = 0
    while pv == 0:
        pv = random_bytes(PRIVATE_VALUE_LEN) % N

    return pv

def compute_client_session_key(k: int, x: int, u: int, a: int, B: int) -> int:
    exp = u * x + a
    temp = (pow(2, x, N) * k) % N

    return pow(B + N - temp, exp, N)

def compute_client_evidence(A:int, B:int, S:int) -> int:
    return btoi(hash(itob(A), itob(B), itob(S)))

def process_challenge(password: str, s: bytes, B: int) -> Tuple[int, int, int, int, int, int, int]:
    x = compute_x(s, password)
    a = generate_private_value()
    A = pow(2, a, N)
    k = btoi(hash_padded(itob(N), b'\x02'))
    u = btoi(hash_padded(itob(A), itob(B)))
    S = compute_client_session_key(k, x, u, a, B)
    M1 = compute_client_evidence(A, B, S)

    return (x, a, A, k, u, S, M1)