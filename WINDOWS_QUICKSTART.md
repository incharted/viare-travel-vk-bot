# Windows Quick Start

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/).
2. Open PowerShell in the project folder.
3. Run:

```powershell
.\scripts\setup.ps1
```

4. Send `/myid` to the bot from your VK account.
5. Add yourself as admin:

```powershell
.\scripts\set-admin.ps1 -VkId 123456789
```

6. Start the bot:

```powershell
.\scripts\run.ps1
```

If `VK_TOKEN` is still a placeholder in `.env`, replace it with the community access token first.
