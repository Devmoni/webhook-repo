# GitHub Webhook Receiver

This repository contains a Flask application that receives GitHub webhooks and stores them in MongoDB.

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up MongoDB:
   - Create a `.env` file in the root directory
   - Add your MongoDB URI:
     ```
     MONGO_URI=your_mongodb_connection_string
     ```

5. Configure GitHub Webhooks:
   - Go to your GitHub repository settings
   - Click on "Webhooks"
   - Add webhook:
     - Payload URL: `http://your-domain/webhook/receiver`
     - Content type: `application/json`
     - Select events: Push, Pull Request, Merge

6. Run the application:
   ```bash
   python run.py
   ```

## Webhook Events Format

The application handles the following GitHub events:

### PUSH
Format: `{author} pushed to {to_branch} on {timestamp}`
Example: "Travis" pushed to "staging" on 1st April 2021 - 9:30 PM UTC

### PULL_REQUEST
Format: `{author} submitted a pull request from {from_branch} to {to_branch} on {timestamp}`
Example: "Travis" submitted a pull request from "staging" to "master" on 1st April 2021 - 9:00 AM UTC

### MERGE
Format: `{author} merged branch {from_branch} to {to_branch} on {timestamp}`
Example: "Travis" merged branch "dev" to "master" on 2nd April 2021 - 12:00 PM UTC

## MongoDB Schema

```json
{
    "_id": "ObjectId",
    "request_id": "string",
    "author": "string",
    "action": "string",
    "from_branch": "string",
    "to_branch": "string",
    "timestamp": "string/datetime"
}
```