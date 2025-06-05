from flask import Blueprint, request, jsonify
from app.extensions import mongo
from datetime import datetime
from app.utils import logger
from functools import wraps
import hmac
import hashlib
import json

webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')

# Define valid action types
VALID_ACTIONS = ["PUSH", "PULL_REQUEST", "MERGE", "WORKFLOW_RUN"]

def validate_webhook_data(data, event_type):
    """Validate webhook payload data"""
    logger.info(f"Validating webhook data for event type: {event_type}")
    logger.info(f"Payload: {json.dumps(data, indent=2)}")
    
    # For ping event, only check zen and hook_id
    if event_type == 'ping':
        return []  # Accept all ping events
    
    # For push events
    if event_type == 'push':
        required_fields = []
        if 'ref' not in data:
            required_fields.append("ref")
        if 'after' not in data:
            required_fields.append("after")
        if required_fields:
            return [f"Missing required fields: {', '.join(required_fields)}"]
        return []
    
    # For workflow_run events
    if event_type == 'workflow_run':
        if 'workflow_run' not in data:
            return ["Missing workflow_run information"]
        workflow_run = data.get('workflow_run', {})
        required_fields = []
        if not workflow_run.get('id'):
            required_fields.append("workflow_run.id")
        if not workflow_run.get('name'):
            required_fields.append("workflow_run.name")
        if not workflow_run.get('status'):
            required_fields.append("workflow_run.status")
        if required_fields:
            return [f"Missing required fields: {', '.join(required_fields)}"]
        return []
    
    return []  # Accept other events

def error_response(message, status_code=400):
    """Generate error response"""
    logger.error(f"Error processing webhook: {message}")
    return jsonify({"error": message}), status_code

@webhook.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }), 200

@webhook.route('/receiver', methods=["POST"])
def receiver():
    try:
        # Log incoming request details
        logger.info("Received webhook request")
        logger.info(f"Headers: {dict(request.headers)}")
        
        payload = request.json
        if not payload:
            logger.error("No payload received")
            return error_response("No payload received")
            
        logger.info(f"Received payload: {json.dumps(payload, indent=2)}")
        
        event_type = request.headers.get('X-GitHub-Event')
        if not event_type:
            logger.error("No event type specified in headers")
            return error_response("No event type specified in headers")
        
        logger.info(f"Processing {event_type} event from GitHub")
        
        # Handle ping event
        if event_type == 'ping':
            return jsonify({
                "message": "Webhook configured successfully",
                "zen": payload.get('zen'),
                "hook_id": payload.get('hook_id')
            }), 200
        
        # Validate payload based on event type
        validation_errors = validate_webhook_data(payload, event_type)
        if validation_errors:
            return error_response(f"Validation errors: {', '.join(validation_errors)}")
        
        try:
            # Store events based on type
            if event_type == 'push':
                # Store push event
                push_data = {
                    'event_type': 'push',
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'ref': payload.get('ref'),
                    'after': payload.get('after'),
                    'repository': payload.get('repository', {}).get('full_name'),
                    'pusher': payload.get('pusher', {}).get('name'),
                    'sender': payload.get('sender', {}).get('login')
                }
                mongo.db.events.insert_one(push_data)
                logger.info("Stored push event in MongoDB")
                
            elif event_type == 'pull_request':
                # Store pull request event
                pr_data = {
                    'event_type': 'pull_request',
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'action': payload.get('action'),
                    'pull_request_id': payload.get('pull_request', {}).get('id'),
                    'title': payload.get('pull_request', {}).get('title'),
                    'from_branch': payload.get('pull_request', {}).get('head', {}).get('ref'),
                    'to_branch': payload.get('pull_request', {}).get('base', {}).get('ref'),
                    'author': payload.get('sender', {}).get('login'),
                    'repository': payload.get('repository', {}).get('full_name'),
                    'merged': payload.get('pull_request', {}).get('merged', False)
                }
                mongo.db.events.insert_one(pr_data)
                logger.info("Stored pull request event in MongoDB")

                # If PR is merged, create a merge event
                if payload.get('action') == 'closed' and payload.get('pull_request', {}).get('merged', False):
                    merge_data = {
                        'event_type': 'merge',
                        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                        'pull_request_id': payload.get('pull_request', {}).get('id'),
                        'from_branch': payload.get('pull_request', {}).get('head', {}).get('ref'),
                        'to_branch': payload.get('pull_request', {}).get('base', {}).get('ref'),
                        'author': payload.get('sender', {}).get('login'),
                        'repository': payload.get('repository', {}).get('full_name'),
                        'merge_commit_sha': payload.get('pull_request', {}).get('merge_commit_sha')
                    }
                    mongo.db.events.insert_one(merge_data)
                    logger.info("Stored merge event in MongoDB")
            
            elif event_type == 'workflow_run':
                # Store workflow notification
                workflow_run = payload.get('workflow_run', {})
                workflow_data = {
                    'event_type': 'workflow_run',
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'workflow_id': workflow_run.get('id'),
                    'workflow_name': workflow_run.get('name'),
                    'status': workflow_run.get('status'),
                    'conclusion': workflow_run.get('conclusion', 'unknown'),
                    'actor': workflow_run.get('actor', {}).get('login'),
                    'repository': payload.get('repository', {}).get('full_name'),
                    'head_branch': workflow_run.get('head_branch'),
                    'head_sha': workflow_run.get('head_sha'),
                    'run_attempt': workflow_run.get('run_attempt', 1),
                    'run_number': workflow_run.get('run_number'),
                    'run_started_at': workflow_run.get('created_at'),
                    'run_updated_at': workflow_run.get('updated_at')
                }
                mongo.db.events.insert_one(workflow_data)
                logger.info("Stored workflow notification in MongoDB")
            
            return jsonify({
                "message": f"Successfully processed {event_type} event",
                "status": "success",
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            }), 200
            
        except Exception as e:
            logger.error(f"Error processing webhook data: {str(e)}")
            return error_response(f"Error processing webhook: {str(e)}")
            
    except Exception as e:
        logger.error(f"Unexpected error in webhook receiver: {str(e)}")
        return error_response("Internal server error", 500)

@webhook.route('/events', methods=['GET'])
def get_events():
    """Get all webhook events from MongoDB"""
    try:
        # Get optional query parameters
        event_type = request.args.get('type')  # 'push' or 'workflow_run'
        status = request.args.get('status')    # for workflow_run events
        limit = int(request.args.get('limit', 10))  # Default to 10 events
        
        # Build query
        query = {}
        if event_type:
            query['event_type'] = event_type
        if status and event_type == 'workflow_run':
            query['status'] = status
        
        # Get events from MongoDB
        events = list(mongo.db.events.find(
            query,
            {'_id': 0}  # Exclude MongoDB _id
        ).sort('timestamp', -1).limit(limit))
        
        return jsonify({
            'count': len(events),
            'events': events
        }), 200
    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        return error_response("Failed to retrieve events", 500)

@webhook.route('/test/push', methods=['GET'])
def test_push():
    """Test endpoint to simulate a push event"""
    try:
        test_data = {
            "sender": {"login": "test-user"},
            "ref": "refs/heads/main",
            "after": "test-commit-" + datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        }
        
        # Store in MongoDB
        event_data = {
            'request_id': test_data['after'],
            'author': test_data['sender']['login'],
            'action': 'PUSH',
            'from_branch': 'main',
            'to_branch': 'main',
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        mongo.db.events.insert_one(event_data)
        
        return jsonify({
            "message": "Test push event created successfully",
            "event_data": event_data
        }), 200
    except Exception as e:
        logger.error(f"Error creating test event: {str(e)}")
        return jsonify({"error": str(e)}), 500

@webhook.route('/test/pull-request', methods=['GET'])
def test_pull_request():
    """Test endpoint to simulate a pull request event"""
    try:
        test_data = {
            "sender": {"login": "test-user"},
            "pull_request": {
                "id": "pr-" + datetime.utcnow().strftime('%Y%m%d-%H%M%S'),
                "head": {"ref": "feature"},
                "base": {"ref": "main"}
            }
        }
        
        # Store in MongoDB
        event_data = {
            'request_id': test_data['pull_request']['id'],
            'author': test_data['sender']['login'],
            'action': 'PULL_REQUEST',
            'from_branch': test_data['pull_request']['head']['ref'],
            'to_branch': test_data['pull_request']['base']['ref'],
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        mongo.db.events.insert_one(event_data)
        
        return jsonify({
            "message": "Test pull request event created successfully",
            "event_data": event_data
        }), 200
    except Exception as e:
        logger.error(f"Error creating test event: {str(e)}")
        return jsonify({"error": str(e)}), 500
