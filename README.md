# 🤖Google Form Auto-Fill Bot(Specially created for WI)

Designed specifically for restricted Google Forms requiring Google account authentication (e.g. `@kalvium.community`), automatically submitting your form every **Monday through Friday at 11:00 AM IST** without requiring your laptop to be turned on!

---

## 👥 How to Set Up This Bot For Yourself (Step-by-Step Guide)

Follow these simple steps to deploy your own automated Google Form submission bot in less than 5 minutes!

---

### Step 1: Fork & Clone the Repository

1. Click **Fork** at the top right of this repository to create your own copy on GitHub.
2. Clone your forked repository to your laptop:
   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/wi-form-automation.git
   cd wi-form-automation
   ```

---

### Step 2: Install Local Dependencies

Set up Python and Playwright on your laptop (required only once to capture your login session):

```bash
# Install Python requirements
pip install -r requirements.txt

# Install Playwright Chromium browser
playwright install chromium
```

---

### Step 3: Configure Your Google Form (`config.json`)

Edit `config.json` with your Google Form URL, submit time, timezone, and answers:

```json
{
  "form_url": "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform",
  "submit_time": "11:00",
  "timezone": "Asia/Kolkata",
  "answers": {
    "Email": "Record your.email@kalvium.community as the email to be included with my response",
    "A confirmation to start with - was today a working day for you?": "It was a working day, and I was present",
    "What were your key tasks for the day?": ".",
    "What challenges/problems did you solve today?": ".",
    "What challenges/problems you were NOT able to solve today and are planning to solve in upcoming days?": ".",
    "What is your plan for the next day of Simulated Work?": "."
  }
}
```

Commit and push your updated `config.json` to your GitHub repository:
```bash
git add config.json
git commit -m "Update config with my form details"
git push
```

---

### Step 4: One-Time Google Account Login Setup

Run the one-time authentication helper to log into your `@kalvium.community` account:

```bash
python main.py --setup-auth
```

1. A browser window will open loading your Google Form.
2. Log into your `@kalvium.community` Google Account.
3. Once your form is visible on screen, return to your terminal and press **ENTER**.
4. Your login cookies are safely saved to `auth.json` on your laptop.

---

### Step 5: Copy your Secret to GitHub Repository Secrets

1. Run the secret helper script in your terminal:
   ```bash
   python print_secret.py
   ```
2. Copy the single-line Base64 secret text printed on your screen.
3. Open your forked repository on **GitHub.com**.
4. Go to **Settings** ➔ **Secrets and variables** ➔ **Actions**.
5. Click **New repository secret**.
6. Set **Name**: `AUTH_JSON`
7. Set **Value**: Paste your copied secret string.
8. Click **Add secret**.

---

### Step 6: Enable & Test your GitHub Action Workflow

1. Go to the **Actions** tab on your GitHub repository.
2. If GitHub prompts you with *"Workflows are disabled"*, click **I understand my workflows, go ahead and enable them**.
3. Select **Daily Google Form Auto-Fill Bot** from the left sidebar.
4. Click **Run workflow** ➔ **Run workflow**.

🎉 **Congratulations!** Your bot will now automatically run every **Monday through Friday at 11:00 AM IST** in the cloud. You can turn off your laptop, and your daily form will continue to be submitted reliably!

---

## THE QUESTION'S WILL GET IN YOUR MIND❓ (FAQ)

<details>
<summary><b>Does my laptop need to stay turned on?</b></summary>
<b>No!</b> GitHub Actions runs on GitHub's cloud servers. Your laptop can be turned off, asleep, or disconnected from the internet.
</details>

<details>
<summary><b>Is my Google password or login safe?</b></summary>
<b>Yes.</b> Your password is never stored or committed. Only encrypted browser session tokens are saved inside your private GitHub Repository Secrets.
</details>

<details>
<summary><b>Where can I check if my form was submitted today?</b></summary>
Check the <b>Actions</b> tab of your GitHub repository. Every daily run will show a green checkmark (<code>✓</code>) along with execution logs.
</details>
