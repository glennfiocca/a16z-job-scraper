# Setting Up Periodic Scraping with GitHub Actions

## Step 1: Create a GitHub Repository

1. Go to GitHub.com and create a new repository
2. Name it something like `a16z-jobs-scraper`
3. Make it public or private (your choice)

## Step 2: Push Your Code to GitHub

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit your changes
git commit -m "Initial commit with batch processing scraper"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/a16z-jobs-scraper.git

# Push to GitHub
git push -u origin main
```

## Step 3: Configure GitHub Actions

The `.github/workflows/scraper.yml` file is already created and will:
- Run every 3 hours automatically
- Process 20 companies per batch (configurable)
- Resume from the last processed company
- Save progress and database as artifacts

## Step 4: Manual Triggering

You can also trigger the scraper manually:
1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "A16Z Jobs Scraper" workflow
4. Click "Run workflow"
5. Optionally set custom batch size and resume settings

## Step 5: Monitor Progress

- Check the "Actions" tab to see run history
- Download artifacts to get the latest database and progress
- View logs to see what companies were processed

## Configuration Options

### Environment Variables (in GitHub Actions)
- `SCRAPER_BATCH_SIZE`: Number of companies to process per batch (default: 20)
- `DATABASE_URL`: Database connection string
- `FLASK_SECRET_KEY`: Secret key for Flask

### Cron Schedule
Current schedule: `0 */3 * * *` (every 3 hours)
- Change to `0 */6 * * *` for every 6 hours
- Change to `0 0 * * *` for once daily
- Change to `0 */2 * * *` for every 2 hours

## Benefits of This Setup

✅ **Free**: GitHub Actions provides 2000 minutes/month free
✅ **Reliable**: Runs automatically without manual intervention
✅ **Resumable**: Continues from where it left off
✅ **Configurable**: Easy to adjust batch size and schedule
✅ **Monitored**: Full logs and progress tracking
✅ **Scalable**: Can process hundreds of companies over time

## Troubleshooting

1. **If the scraper stops unexpectedly**: Check the Actions logs for errors
2. **If you want to start over**: Delete the `scraping_progress.json` file and push
3. **If you want to change the schedule**: Edit the cron expression in `.github/workflows/scraper.yml`
4. **If you want to process more companies per batch**: Increase the `SCRAPER_BATCH_SIZE` environment variable
