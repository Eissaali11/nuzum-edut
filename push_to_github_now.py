import os
import subprocess
import sys

REPO_PATH = r"D:\nuzm"
REMOTE_URL = "https://github.com/Eissaali11/nuzum-edut.git"
GIT = r"C:\Program Files\Git\bin\git.exe"


def run(*args, check=True):
    print("$", " ".join(args))
    p = subprocess.run(args, cwd=REPO_PATH, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout.strip())
    if p.stderr:
        print(p.stderr.strip())
    if check and p.returncode != 0:
        raise SystemExit(p.returncode)
    return p


def main():
    if not os.path.exists(GIT):
        print("Git not found:", GIT)
        raise SystemExit(1)

    os.makedirs(REPO_PATH, exist_ok=True)

    # init if needed
    p = run(GIT, "rev-parse", "--is-inside-work-tree", check=False)
    if p.returncode != 0:
        run(GIT, "init")

    # ensure identity
    run(GIT, "config", "user.name", "NUZUM System")
    run(GIT, "config", "user.email", "admin@nuzum.local")

    # stage + commit (allow no-op)
    run(GIT, "add", ".")
    commit = run(GIT, "commit", "-m", "Initial commit: NUZUM project upload", check=False)
    if commit.returncode != 0:
        print("No new commit created (possibly nothing to commit).")

    # set branch main
    run(GIT, "branch", "-M", "main", check=False)

    # set remote origin
    remotes = run(GIT, "remote", check=False)
    remote_names = set(remotes.stdout.split()) if remotes.stdout else set()
    if "origin" in remote_names:
        run(GIT, "remote", "set-url", "origin", REMOTE_URL)
    else:
        run(GIT, "remote", "add", "origin", REMOTE_URL)

    # push
    push = run(GIT, "push", "-u", "origin", "main", check=False)
    if push.returncode == 0:
        print("\nSUCCESS: pushed to", REMOTE_URL)
        return

    print("\nPush failed. Most likely authentication is required.")
    print("Use Git Credential Manager popup or run this once manually:")
    print(f'  "{GIT}" push -u origin main')
    raise SystemExit(push.returncode)


if __name__ == "__main__":
    main()
