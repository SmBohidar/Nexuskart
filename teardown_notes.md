# NexusKart: AWS Teardown & Disconnection Guide

Since your AWS Free Tier expires in 6 months, it is **critical** to properly shut down your resources before you start getting billed. Simply closing the browser or forgetting about the account will result in monthly credit card charges.

Follow this guide step-by-step when you are ready to take the website offline permanently.

---

## Step 1: Backup Your Live Database (IMPORTANT)
Before destroying the server, you should download a copy of your live production database so you don't lose all your users, orders, and products.

1. SSH into your AWS server one last time:
   ```bash
   ssh -i "Nexuskart.pem" ubuntu@15.206.75.237
   ```
2. Run this command to export your PostgreSQL database into a single backup file:
   ```bash
   pg_dump -U postgres -h nexuskart-db.chc6ymeeuxo6.ap-south-1.rds.amazonaws.com nexuskart_db > nexuskart_backup.sql
   ```
3. Type `exit` to disconnect from the server.
4. On your **local laptop terminal**, run this command to download the backup file to your computer:
   ```bash
   scp -i "Nexuskart.pem" ubuntu@15.206.75.237:/home/ubuntu/nexuskart_backup.sql ./
   ```
   *(Keep this `nexuskart_backup.sql` file safe. If you ever deploy the site again in the future, you can import this file to restore all your data!)*

---

## Step 2: Terminate the AWS EC2 Server
You must fully "Terminate" the server, not just "Stop" it. Stopped servers still charge you for the hard drive storage attached to them.

1. Log into your **AWS Console** and go to the **EC2 Dashboard**.
2. Click on **Instances (running)**.
3. Check the box next to your NexusKart server.
4. Click the **Instance state** dropdown at the top.
5. Select **Terminate instance** (and confirm the warning).
   *(This permanently deletes the virtual computer and its hard drive).*

---

## Step 3: Delete the AWS RDS Database
RDS databases are the most expensive part of AWS if left running.

1. In the AWS Console, search for **RDS** at the very top.
2. Click on **Databases** on the left menu.
3. Select your `nexuskart-db` instance.
4. Click the **Actions** dropdown and select **Delete**.
5. **Crucial:** It will ask if you want to create a "Final Snapshot" (backup). Uncheck this box! If you create a snapshot, AWS will charge you monthly storage fees to keep it forever. (We already did a manual backup in Step 1).
6. Type `delete me` (or whatever phrase it requires) to confirm deletion.

---

## Step 4: Release Elastic IP Addresses (If Applicable)
If you generated a static Elastic IP address for your server during setup, you must release it. AWS charges money for Elastic IPs that are *not* attached to a running server!

1. Go back to the **EC2 Dashboard**.
2. Scroll down the left menu and click on **Elastic IPs** (under Network & Security).
3. If there is an IP address listed there, select it.
4. Click **Actions** -> **Release Elastic IP addresses**.

---

## Step 5: Disconnect the Domain Name (Hostinger)
Your domain (`nexuskart.online`) will remain yours for a full 12 months, but we need to disconnect it from the dead AWS IP address so visitors don't get an ugly security error.

1. Log into your **Hostinger Dashboard**.
2. Go to **Domains** -> **Manage** -> **DNS / Nameservers**.
3. Look at your list of DNS records. Find the **A Record** that points to `15.206.75.237`.
4. Click the **Trash Can** icon to delete it.
5. If you want, you can create a new A Record pointing to a free hosting service (like Vercel or Render) if you decide to host a simpler version of the site there later.

---

## Step 6: Revoke Google OAuth Credentials
For security hygiene, you should disable the Google Login connection.

1. Go to the **Google Cloud Console**.
2. Navigate to **APIs & Services** -> **Credentials**.
3. Click the Trash Can icon next to your NexusKart OAuth 2.0 Client ID to permanently delete it.

---

### Final Check
After completing these steps, your AWS bill will immediately drop to $0.00. You can go to the AWS Billing Dashboard just to verify that no active resources are racking up charges. Your website is now safely offline!
