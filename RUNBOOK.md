# Runbook: restarting and fixing the LSEG RAG Assistant

Use this when you want to show the project live after it has been stopped for days, weeks or months. Each problem has its own section, so jump to the one you need.

**Fixed values for this project**

| Item | Value |
|---|---|
| SSH user | `ubuntu` (not `ec2-user`) |
| Key file | `C:\Users\moham\.ssh\lseg_rag_KEY_PAIR.pem` |
| Project folder on server | `~/lseg-rag-assistant` |
| Data folder on server | `~/app-data/` (holds `.env`, `chroma_db/`, `logs/`, `data/`) |
| Container name | `rag` |
| Image name | `lseg-rag` |
| Port | `8000` |
| Server env file | `~/app-data/.env` |

The public IP changes every time the instance is stopped and started. Everything below uses `NEW_IP` for the address you copy from the AWS console.

---

## Contents

1. [Start the demo (normal case)](#1-start-the-demo-normal-case)
2. [Page does not load](#2-page-does-not-load)
3. [Page says `{"detail":"Not Found"}`](#3-page-says-detailnot-found)
4. [Asking a question shows an error](#4-asking-a-question-shows-an-error)
5. [SSH will not connect](#5-ssh-will-not-connect)
6. [Container is not running](#6-container-is-not-running)
7. [GitHub Action deploy fails](#7-github-action-deploy-fails)
8. [Server is out of disk space or memory](#8-server-is-out-of-disk-space-or-memory)
9. [Instance will not start or is gone](#9-instance-will-not-start-or-is-gone)
10. [Costs and billing surprises](#10-costs-and-billing-surprises)
11. [Stop the demo](#11-stop-the-demo)
12. [Backup plan if nothing works](#12-backup-plan-if-nothing-works)

---

## 1. Start the demo (normal case)

Do this **the day before** you need to show this, not five minutes before.

1. Open the AWS console, then **EC2, Instances**.
2. Tick `lseg-rag`, then **Instance state, Start instance**.
3. Wait for **Running** and for the status checks to pass (about 1 to 2 minutes).
4. Copy the new **Public IPv4 address**.
5. Wait one more minute. The container starts itself, then loads the embedding model and keyword index.
6. Open `http://NEW_IP:8000/health`. Expected: `{"status": "ok"}`.
7. Open `http://NEW_IP:8000/` and ask a question, for example "What was total income excluding recoveries in 2025?". Expected: an answer of £8,986 million with page tabs.
8. Ask one question the reports cannot answer, for example "What is the capital of France?". Expected: "I don't know based on the provided documents."

You do **not** need to change any GitHub secret, the security group or any server file for a demo. If everything works, skip to [section 11](#11-stop-the-demo) when you finish.

---

## 2. Page does not load

Symptom: the browser spins or says the site can't be reached.

Check in this order:

1. **Is the instance Running?** In the EC2 console the state must be `Running`, not `Stopped` or `Pending`.
2. **Are you using the new IP?** The old IP stops working after every stop and start. Copy it again from the console.
3. **Did you type `http://` and not `https://`?** The server has no HTTPS. Use `http://NEW_IP:8000/`.
4. **Wait two minutes.** Right after a start the container is still loading.
5. **Check the security group.** EC2, your instance, **Security**, click the security group, **Inbound rules**. It must allow:
   - Custom TCP, port `8000`, source `0.0.0.0/0`
   - SSH, port `22`, source `0.0.0.0/0` (needed for GitHub deploys) or your own IP (enough for a demo)
6. **Try another network.** Some office and college networks block port 8000. Try a phone hotspot.
7. If the health page still fails, go to [section 6](#6-container-is-not-running).

---

## 3. Page says `{"detail":"Not Found"}`

Symptom: `/docs` works but `/` shows `Not Found`.

Cause: the server is running an older version of the code (before the UI was added), or a deploy is still building.

1. Open the repo's **Actions** tab on GitHub. If the latest run is **yellow**, wait until it is **green**, then reload the page.
2. If the latest run is **red**, see [section 7](#7-github-action-deploy-fails).
3. If it is green and the page is still wrong, rebuild by hand. SSH in ([section 5](#5-ssh-will-not-connect)) and run:
   ```bash
   cd ~/lseg-rag-assistant
   git pull origin main
   ls app/static          # must show index.html
   docker build -t lseg-rag .
   docker rm -f rag
   docker run -d --name rag --restart unless-stopped -p 8000:8000 \
     --env-file ~/app-data/.env \
     -v ~/app-data/chroma_db:/code/chroma_db \
     -v ~/app-data/logs:/code/logs \
     lseg-rag
   docker logs rag --tail 20
   ```
4. If `ls app/static` shows nothing, the file was never committed. On your laptop run `git status`, then `git add app/static/index.html`, commit and push.

---

## 4. Asking a question shows an error

The page loads but the answer box shows a red error. Find your case below. First, look at the container logs, because they show the real error:

```bash
ssh -i C:\Users\moham\.ssh\lseg_rag_KEY_PAIR.pem ubuntu@NEW_IP
docker logs rag --tail 40
```

### 4a. "Model not found" or a 404 from Gemini

Cause: Google retired the model name (this already happened to `gemini-2.5-flash`).

1. Open Google AI Studio and look at the current model list. Pick a recent **Flash** model. Skip names containing `preview`, `exp`, `image`, `tts`, `live` or `transcribe`.
2. Edit the env file on the server:
   ```bash
   nano ~/app-data/.env
   ```
   Change the line `GEMINI_MODEL=...` to the new name. Save with `Ctrl+O`, Enter, `Ctrl+X`.
3. **Recreate** the container. `docker restart rag` does NOT re-read the env file.
   ```bash
   docker rm -f rag
   docker run -d --name rag --restart unless-stopped -p 8000:8000 \
     --env-file ~/app-data/.env \
     -v ~/app-data/chroma_db:/code/chroma_db \
     -v ~/app-data/logs:/code/logs \
     lseg-rag
   ```
4. Wait a minute and ask a question again.

### 4b. API key invalid, expired or revoked (401, 403 or "API key not valid")

1. Open AI Studio, create a new API key and copy it with the copy button. Do not screenshot it or paste it anywhere public.
2. Edit `~/app-data/.env` on the server and replace `GEMINI_API_KEY=...`.
3. Recreate the container with the `docker rm -f rag` and `docker run ...` commands from 4a.

### 4c. Rate limit or overload (429 or 503)

Symptom: "The language model didn't respond", or logs mention `429` or `503 UNAVAILABLE`.

This is temporary on the free tier. Wait one minute and ask again. If it keeps happening, set `GEMINI_MODEL` to a lighter model (a "flash-lite" variant) as in 4a.

### 4d. "I don't know" for a question the reports can answer

Not a server fault. Retrieval is sensitive to wording. Rephrase using the report's own words, include the year, and name the figure ("total income excluding recoveries in 2025"). This is a documented limitation in the README.

### 4e. Error about `chroma_db` or collection `lseg` not found

Cause: the index folder is missing or empty. Rebuild it:

```bash
ls -lh ~/app-data/data          # must show the 3 PDFs
docker run --rm \
  -v ~/app-data/data:/code/data \
  -v ~/app-data/chroma_db:/code/chroma_db \
  lseg-rag python app/ingest.py
```
Expected last line: `Done. Stored 1740 chunks.` Then recreate the container (commands in 4a).

If the PDFs are missing, copy them again from your laptop (run this on the laptop, not on the server):

```powershell
scp -i C:\Users\moham\.ssh\lseg_rag_KEY_PAIR.pem C:\Users\moham\Desktop\lseg-rag-assistant\data\*.pdf ubuntu@NEW_IP:~/app-data/data/
```

---

## 5. SSH will not connect

Connect with:

```powershell
ssh -i C:\Users\moham\.ssh\lseg_rag_KEY_PAIR.pem ubuntu@NEW_IP
```

| Message | Cause | Fix |
|---|---|---|
| `Connection timed out` | Instance stopped, old IP, or port 22 blocked | Check state is Running, use the new IP, check the security group allows port 22 from your current IP |
| `Permission denied (publickey)` | Wrong user or wrong key | Use user `ubuntu`, not `ec2-user`. Make sure the key file is the one chosen when the instance was launched |
| `UNPROTECTED PRIVATE KEY FILE` or `bad permissions` | Windows file permissions too open | Run the two `icacls` commands below |
| `Identity file ... not accessible` | Wrong path or file moved | Check the path with `dir C:\Users\moham\.ssh` |
| Hostname error mentioning `your_public_ip` | Placeholder typed instead of the real IP | Replace `NEW_IP` with the real address |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | An old entry for that IP is in `known_hosts` | `ssh-keygen -R NEW_IP`, then connect again |

Fix key permissions (PowerShell):

```powershell
icacls C:\Users\moham\.ssh\lseg_rag_KEY_PAIR.pem /inheritance:r
icacls C:\Users\moham\.ssh\lseg_rag_KEY_PAIR.pem /grant:r "$($env:USERNAME):(R)"
```

If your IP changed since you last connected and port 22 is limited to "My IP", edit the security group's SSH rule and choose **My IP** again.

If the `.pem` file is lost, it cannot be re-downloaded. You would need to create a new key pair and launch a new instance, then repeat the server setup (see [section 9](#9-instance-will-not-start-or-is-gone)).

---

## 6. Container is not running

Symptom: `/health` does not respond but the instance is Running.

SSH in, then:

```bash
docker ps -a
docker logs rag --tail 40
```

| What you see | Fix |
|---|---|
| `rag` is listed as `Exited` | Run `docker start rag`, then check `docker logs rag --tail 20` |
| `rag` is not listed at all | Recreate it with the `docker run` command from 4a |
| Docker itself is not running | `sudo systemctl start docker`, then `docker start rag` |
| `permission denied` on `docker` | Run `sudo usermod -aG docker ubuntu`, type `exit`, and SSH in again |
| Logs show `Killed` | Out of memory, see [section 8](#8-server-is-out-of-disk-space-or-memory) |
| Logs show `ModuleNotFoundError` | The image was built without a package. Check `requirements.txt` in the repo, push, and let the deploy rebuild, or rebuild by hand as in section 3 |
| Image `lseg-rag` does not exist | Rebuild: `cd ~/lseg-rag-assistant && docker build -t lseg-rag .` then recreate the container |

A healthy log ends with:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 7. GitHub Action deploy fails

A red X on the Actions tab. First, **find the real error**:

1. Click the failed run, then the **deploy** job, then expand **Deploy over SSH**.
2. Read the last 20 lines.

| Error | Cause | Fix |
|---|---|---|
| `i/o timeout` or `connection refused` | Instance stopped, or `EC2_HOST` is the old IP, or port 22 is closed to GitHub | Start the instance, update the `EC2_HOST` secret with the new IP, open SSH (port 22) to `0.0.0.0/0`, then **Re-run all jobs** |
| `handshake failed` or `no supported methods remain` | `EC2_SSH_KEY` secret is wrong or incomplete | Re-paste the whole `.pem` file including the `BEGIN` and `END` lines |
| `Run Command Timeout` or the run dies after about 10 minutes | The build on the small server is slow | Add `command_timeout: 30m` under `with:` in `deploy.yml`, then re-run |
| `git pull` error | Local changes on the server | On the server: `cd ~/lseg-rag-assistant && git status`. If safe: `git reset --hard origin/main` |
| `Killed` during `docker build` | Out of memory | See [section 8](#8-server-is-out-of-disk-space-or-memory) |
| `no space left on device` | Disk full | See [section 8](#8-server-is-out-of-disk-space-or-memory) |

To update the secret: GitHub repo, **Settings, Secrets and variables, Actions**, edit `EC2_HOST`.

Rules that avoid most failures:

- Start the instance and update `EC2_HOST` **before** you push.
- Wait for the **green** check before testing the site or running the eval. While the run is yellow, the old container is still answering.
- A transient failure often passes on **Re-run all jobs** with no change.

---

## 8. Server is out of disk space or memory

### Out of disk space

```bash
df -h /
docker system df
```

Free space safely:

```bash
docker image prune -f           # removes dangling images
docker builder prune -f         # removes build cache
```

Only if you still need more, remove unused images (the running container is unaffected):

```bash
docker image prune -a -f
```

Then rebuild if needed. If the disk is still too small, enlarge the EBS volume in the AWS console (EC2, Volumes, Modify volume), then run `sudo growpart /dev/nvme0n1 1` and `sudo resize2fs /dev/nvme0n1p1`. Check the device name with `lsblk` first.

### Out of memory

```bash
free -h
```

Swap should show about 2 GB. If it shows `0B`:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h
```

Add it to `/etc/fstab` only once, with `grep swapfile /etc/fstab` to check first. If `fallocate` says "Text file busy", swap is already active and nothing is needed.

If builds are still killed, stop the container during the build (`docker stop rag`), build, then start it again.

---

## 9. Instance will not start or is gone

- **Stuck on Pending or fails to start:** wait a few minutes and try again. If it keeps failing, choose **Instance state, Stop**, wait, then **Start**.
- **"Insufficient capacity" error:** AWS has no room for that instance type in that zone right now. Try again later.
- **Instance was terminated or deleted:** the disk is gone with it. Rebuild from scratch:
  1. Launch a new Ubuntu 24.04 x86 instance (free-tier eligible type, 20 GB disk). Open ports 22 and 8000 in the security group. Create a new key pair and save it safely.
  2. Install Docker: `sudo apt update && sudo apt install -y docker.io`, then `sudo usermod -aG docker ubuntu`, `exit`, and SSH in again.
  3. Add 2 GB swap (section 8).
  4. `mkdir -p ~/app-data/data ~/app-data/chroma_db ~/app-data/logs`
  5. Copy the 3 PDFs with `scp` (command in 4e).
  6. Create `~/app-data/.env` with `GEMINI_API_KEY`, `GEMINI_MODEL`, `PRICE_IN_PER_M`, `PRICE_OUT_PER_M`, then `chmod 600 ~/app-data/.env`.
  7. `git clone https://github.com/mohammed123-code/lseg-rag-assistant.git && cd lseg-rag-assistant`
  8. Build the image, build the index and run the container (sections 3 and 4e).
  9. Update the GitHub secrets `EC2_HOST` and `EC2_SSH_KEY`.

---

## 10. Costs and billing surprises

- An instance that is **Stopped** does not bill for compute, but its disk (EBS) still exists and counts against the free allowance or costs a small amount.
- A **Running** instance keeps costing or using free-tier hours. Always stop it after a demo.
- A public IPv4 address can be billed on some plans while attached to a running instance. Check **Billing, Free tier** for what your account includes.
- Keep the **zero spend budget** alert on. If you get an email, open **Billing, Bills** to see what is charging, then stop or delete it.
- Do not create an Elastic IP unless you want one. An unattached Elastic IP is billed.
- **Stop** the instance (keeps your data). **Terminate** deletes it and everything on it.

---

## 11. Stop the demo

1. AWS console, **EC2, Instances**, tick `lseg-rag`.
2. **Instance state, Stop instance** (not Terminate).
3. Wait for the state to say **Stopped**.

---

## 12. Backup plan if nothing works

If the live server cannot be fixed in time, present the project from the repo:

1. Open the GitHub README. It has the architecture diagram, the screenshot, the demo GIF and the results table.
2. Walk through: the problem, the pipeline, the evaluation (70% to 100%), what failed and how it was fixed, the limitations.
3. Say: "The live demo runs on a free-tier EC2 instance that I stop to avoid costs. The screenshots and recording show it running, and I can start it on request."

---

## Quick reference: commands

Recreate the container (after any `.env` change):

```bash
docker rm -f rag
docker run -d --name rag --restart unless-stopped -p 8000:8000 \
  --env-file ~/app-data/.env \
  -v ~/app-data/chroma_db:/code/chroma_db \
  -v ~/app-data/logs:/code/logs \
  lseg-rag
```

Rebuild from the latest code:

```bash
cd ~/lseg-rag-assistant && git pull origin main && docker build -t lseg-rag .
```

Look at problems:

```bash
docker ps -a
docker logs rag --tail 40
free -h
df -h /
```

Rebuild the index (only if `chroma_db` is missing):

```bash
docker run --rm -v ~/app-data/data:/code/data -v ~/app-data/chroma_db:/code/chroma_db \
  lseg-rag python app/ingest.py
```

Where requests are logged (latency, tokens, cost per request):

```bash
tail -n 5 ~/app-data/logs/requests.jsonl
```
