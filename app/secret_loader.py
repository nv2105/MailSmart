import os
import base64
import tempfile

def ensure_secret_file(env_path_var: str, relative_path: str, b64_env_var: str = None):
    """
    Ensures a secret JSON file exists and returns its path.
    Checks:
      1) env var path
      2) common secret mounts
      3) relative path inside repo
      4) base64 env var (decode to temp file)
    """
    # 1) explicit path from env var
    explicit = os.environ.get(env_path_var)
    if explicit and os.path.exists(explicit):
        return explicit

    # 2) common secret mount paths
    basename = os.path.basename(relative_path)
    candidates = [
        os.path.join("/run/secrets", basename),
        os.path.join("/etc/secrets", basename),
        os.path.abspath(relative_path)
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return cand

    # 3) base64 env var -> write temp file
    if b64_env_var:
        b64 = os.environ.get(b64_env_var)
        if b64:
            data = base64.b64decode(b64)
            fd, path = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return path

    return None
