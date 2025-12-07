# Deployment Guide - Free Hosting on Render

This guide will help you deploy your D&D Dungeon Manager application to Render.com for free.

## Prerequisites

1. A GitHub account (or GitLab/Bitbucket)
2. A MongoDB Atlas account (free tier available)
3. An OpenAI API key (for character creation features)
4. A Render.com account (free tier available)

## Step 1: Set Up MongoDB Atlas (Free Database)

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Create a free account and cluster (M0 Free Tier)
3. Create a database user:
   - Go to "Database Access" → "Add New Database User"
   - Choose "Password" authentication
   - Save the username and password
4. Whitelist IP addresses:
   - Go to "Network Access" → "Add IP Address"
   - Click "Allow Access from Anywhere" (or add Render's IP ranges)
5. Get your connection string:
   - Go to "Database" → "Connect" → "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password
   - Replace `<dbname>` with `dnd_dungeon` (or your preferred database name)
   - Example: `mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/dnd_dungeon?retryWrites=true&w=majority`

## Step 2: Push Your Code to GitHub

1. If you haven't already, initialize a git repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Create a new repository on GitHub

3. Push your code:
   ```bash
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git branch -M main
   git push -u origin main
   ```

## Step 3: Deploy to Render

1. Go to [Render.com](https://render.com) and sign up/login

2. Click "New +" → "Web Service"

3. Connect your GitHub repository:
   - Select your repository
   - Render will detect it's a Python application

4. Configure the service:
   - **Name**: `dnd-dungeon-manager` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT web.web_app:app`
   - **Plan**: Select "Free" (or "Starter" if you want more resources)

5. Set Environment Variables:
   Click "Add Environment Variable" and add:
   - `MONGODB_URI`: Your MongoDB Atlas connection string from Step 1
   - `DB_NAME`: `dnd_dungeon` (or your preferred database name)
   - `OPENAI_API_KEY`: Your OpenAI API key (get one from [OpenAI](https://platform.openai.com/api-keys))
   - `SECRET_KEY`: Generate a random secret key (you can use: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `PORT`: `10000` (Render sets this automatically, but you can specify it)
   - `FLASK_DEBUG`: `False` (for production)

6. Click "Create Web Service"

7. Wait for deployment:
   - Render will build and deploy your application
   - This usually takes 5-10 minutes
   - You can watch the build logs in real-time

8. Once deployed, your app will be available at:
   `https://your-app-name.onrender.com`

## Step 4: Initialize Database Indexes

After your first deployment, you may want to initialize the database indexes:

1. Go to your Render service dashboard
2. Click "Shell" to open a terminal
3. Run:
   ```bash
   python web/app_start.py
   ```

Alternatively, the indexes are automatically created when the app starts (see `web/web_app.py`).

## Step 5: Access Your Application

1. Visit your Render URL: `https://your-app-name.onrender.com`
2. Register a new account
3. Start creating dungeons and characters!

## Important Notes

### Free Tier Limitations

- **Render Free Tier**:
  - Services spin down after 15 minutes of inactivity
  - First request after spin-down may take 30-60 seconds
  - 750 hours/month of runtime (enough for always-on if you upgrade)
  - 100GB bandwidth/month

- **MongoDB Atlas Free Tier**:
  - 512MB storage
  - Shared cluster resources
  - Perfect for development and small projects

### Security Best Practices

1. **Never commit secrets**: Make sure `.env` is in your `.gitignore`
2. **Use strong SECRET_KEY**: Generate a random 32+ character string
3. **MongoDB Security**: Use strong passwords and restrict network access when possible
4. **OpenAI API Key**: Keep it secure and monitor usage

### Troubleshooting

#### App won't start
- Check build logs in Render dashboard
- Verify all environment variables are set correctly
- Ensure `requirements.txt` has all dependencies

#### Database connection errors
- Verify MongoDB URI is correct
- Check that IP whitelist includes Render's IPs (or allows all)
- Ensure database user has proper permissions

#### Slow first request
- This is normal on free tier (service spins down after inactivity)
- Consider upgrading to paid tier for always-on service

#### Character creation not working
- Verify `OPENAI_API_KEY` is set correctly
- Check OpenAI API usage/credits

## Alternative Free Hosting Options

If Render doesn't work for you, here are other free options:

1. **Railway** (https://railway.app)
   - $5 free credit monthly
   - Similar setup process
   - Better for always-on services

2. **Fly.io** (https://fly.io)
   - Free tier available
   - Good for global distribution
   - More complex setup

3. **PythonAnywhere** (https://www.pythonanywhere.com)
   - Free tier available
   - Limited to one web app
   - Good for simple deployments

## Updating Your Application

To update your application:

1. Make changes to your code locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```
3. Render will automatically detect the push and redeploy
4. Monitor the deployment in the Render dashboard

## Support

If you encounter issues:
1. Check Render build/deploy logs
2. Check application logs in Render dashboard
3. Verify all environment variables are correct
4. Test MongoDB connection separately if needed

Happy deploying! 🎲

