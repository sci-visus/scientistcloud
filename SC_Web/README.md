# ScientistCloud Data Portal

A modular web interface for the ScientistCloud data portal that integrates with the scientistCloudLib for MongoDB access and user management.

## Structure

```
scientistcloud/SC_Web/
├── index.php                 # Main entry point
├── config.php               # Configuration and scientistCloudLib integration
├── login.php                # Authentication page
├── includes/                # PHP modules
│   ├── auth.php            # Authentication management
│   ├── dataset_manager.php # Dataset operations
│   ├── dashboard_manager.php # Dashboard and viewer management
│   ├── dataset_list.php    # Dataset listing component
│   └── dashboard_loader.php # Dashboard loading component
├── api/                     # API endpoints
│   ├── datasets.php        # Get user datasets
│   ├── dataset-details.php # Get dataset details
│   ├── dataset-status.php  # Get dataset status
│   ├── delete-dataset.php  # Delete dataset
│   └── share-dataset.php   # Share dataset
├── assets/                  # Static assets
│   ├── css/
│   │   └── main.css        # Main stylesheet
│   ├── js/
│   │   ├── main.js        # Main JavaScript
│   │   ├── dataset-manager.js # Dataset management
│   │   └── viewer-manager.js  # Viewer management
│   └── images/             # Images and icons
└── logs/                   # Application logs
```

## Features

### Left Sidebar
- **Dataset List**: Displays user's datasets organized by folders
- **Categories**: My Datasets, Shared with Me, Team Datasets
- **Search**: Filter datasets by name
- **Status Indicators**: Visual status badges for each dataset

### Main Content Area
- **Dashboard Loader**: Loads the appropriate dashboard based on user preferences
- **Viewer Toolbar**: Controls for switching between different viewers
- **Status Handling**: Processing, ready, unsupported, and error states
- **Responsive Design**: Adapts to different screen sizes

### Right Sidebar
- **Dataset Details**: Shows detailed information about the selected dataset
- **Actions**: View, share, and delete dataset options
- **Metadata**: File size, creation date, dimensions, etc.

## Integration with scientistCloudLib

The portal integrates with the scientistCloudLib through:

1. **Configuration**: Uses `SCLib_Config` for database and server settings
2. **MongoDB Connection**: Uses `SCLib_MongoConnection` for database operations
3. **Authentication**: Integrates with Auth0 for user management
4. **Job Processing**: Connects to the job processing system for dataset operations

## Configuration

The portal uses environment variables and configuration files:

- **Database**: MongoDB connection via scientistCloudLib
- **Authentication**: Auth0 integration
- **File Storage**: Configurable upload and converted data directories
- **Viewers**: Support for OpenVisus, Bokeh, Jupyter, Plotly, and VTK

## API Endpoints

### GET /api/datasets.php
Returns user's datasets, folders, and statistics.

### GET /api/dataset-details.php?dataset_id={id}
Returns detailed information about a specific dataset.

### GET /api/dataset-status.php?dataset_id={id}
Returns the current status of a dataset.

### POST /api/delete-dataset.php
Deletes a dataset and associated files.

### POST /api/share-dataset.php
Shares a dataset with other users.

## JavaScript Modules

### main.js
- Application initialization
- Theme management
- Sidebar controls
- Global event handling

### dataset-manager.js
- Dataset operations
- Dataset selection
- Details display
- Search and filtering

### viewer-manager.js
- Dashboard loading
- Viewer switching
- Status management
- Error handling

## Styling

The portal uses a modular CSS approach with:
- CSS custom properties for theming
- Responsive design
- Dark/light theme support
- Bootstrap integration

## Usage

1. **Setup**: Configure environment variables and database connection
2. **Authentication**: Users log in through the login page
3. **Navigation**: Browse datasets in the left sidebar
4. **Viewing**: Select a dataset to view in the main area
5. **Details**: View dataset information in the right sidebar

## Dependencies

- PHP 7.4+
- MongoDB
- scientistCloudLib
- Bootstrap 5.3
- FontAwesome 6.4
- Auth0 (for authentication)

## Development

To extend the portal:

1. **Add new viewers**: Update the viewer configuration in `dashboard_manager.php`
2. **Add new API endpoints**: Create new files in the `api/` directory
3. **Modify UI**: Update the CSS and JavaScript files
4. **Add new features**: Extend the existing modules or create new ones

## Security

- Authentication required for all operations
- User access control for datasets
- Input validation and sanitization
- CORS headers for API requests
- Error logging and monitoring
