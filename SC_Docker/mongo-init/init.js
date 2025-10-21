// MongoDB initialization script for ScientistCloud Data Portal
// This creates the necessary collections and indexes

// Switch to the scientistcloud database
db = db.getSiblingDB('scientistcloud');

// Create collections
db.createCollection('visstoredatas');
db.createCollection('user_profile');
db.createCollection('teams');
db.createCollection('shared_user');
db.createCollection('shared_team');
db.createCollection('admins');
db.createCollection('jobs');
db.createCollection('job_logs');
db.createCollection('job_metrics');
db.createCollection('worker_stats');

// Create indexes for better performance
db.visstoredatas.createIndex({ "uuid": 1 }, { unique: true });
db.visstoredatas.createIndex({ "user_id": 1 });
db.visstoredatas.createIndex({ "team_id": 1 });
db.visstoredatas.createIndex({ "folder_uuid": 1 });
db.visstoredatas.createIndex({ "status": 1 });
db.visstoredatas.createIndex({ "created_at": 1 });

db.user_profile.createIndex({ "email": 1 }, { unique: true });
db.user_profile.createIndex({ "team_id": 1 });

db.teams.createIndex({ "name": 1 });
db.teams.createIndex({ "members": 1 });

db.jobs.createIndex({ "status": 1 });
db.jobs.createIndex({ "created_at": 1 });
db.jobs.createIndex({ "user_id": 1 });

// Insert sample data for testing
db.user_profile.insertOne({
    "_id": ObjectId("507f1f77bcf86cd799439011"),
    "email": "test@scientistcloud.com",
    "name": "Test User",
    "preferred_dashboard": "openvisus",
    "team_id": null,
    "permissions": ["read", "upload"],
    "created_at": new Date(),
    "updated_at": new Date()
});

db.visstoredatas.insertMany([
    {
        "_id": ObjectId("507f1f77bcf86cd799439012"),
        "uuid": "test-dataset-1",
        "name": "Sample Dataset 1",
        "sensor": "TIFF",
        "status": "done",
        "compression_status": "compressed",
        "time": "2025-01-20T10:00:00Z",
        "data_size": 1024000,
        "dimensions": "1024x1024x100",
        "google_drive_link": null,
        "folder_uuid": "folder-1",
        "team_uuid": "",
        "user_id": "507f1f77bcf86cd799439011",
        "tags": ["test", "sample"],
        "created_at": new Date(),
        "updated_at": new Date()
    },
    {
        "_id": ObjectId("507f1f77bcf86cd799439013"),
        "uuid": "test-dataset-2",
        "name": "Sample Dataset 2",
        "sensor": "HDF5",
        "status": "processing",
        "compression_status": "uncompressed",
        "time": "2025-01-20T11:00:00Z",
        "data_size": 2048000,
        "dimensions": "512x512x200",
        "google_drive_link": "https://example.com/dataset2",
        "folder_uuid": "folder-2",
        "team_uuid": "",
        "user_id": "507f1f77bcf86cd799439011",
        "tags": ["hdf5", "scientific"],
        "created_at": new Date(),
        "updated_at": new Date()
    }
]);

print("ScientistCloud database initialized successfully!");
print("Collections created: visstoredatas, user_profile, teams, shared_user, shared_team, admins, jobs, job_logs, job_metrics, worker_stats");
print("Sample data inserted for testing");
