# ScientistCloud Data Portal - Testing Guide

## 🚀 Quick Start Testing

The website is now running on **http://localhost:8000** with mock data for testing.

### Test URLs:
- **Main Test Page**: http://localhost:8000/test-index.php
- **Original HTML**: http://localhost:8000/sc_index.html
- **PHP Test Script**: http://localhost:8000/test-php.php

## 🧪 Testing Features

### 1. **Left Sidebar - Dataset Navigation**
- ✅ **My Datasets** section with 2 sample datasets
- ✅ **Folder Organization** with collapsible folders
- ✅ **Status Indicators** (done, processing, error)
- ✅ **File Type Icons** (TIFF, HDF5, etc.)
- ✅ **Search Functionality** (type in search box)
- ✅ **Responsive Collapse** (click arrow buttons)

### 2. **Main Content - Dashboard Area**
- ✅ **Welcome Screen** with user statistics
- ✅ **Dashboard Loading** when dataset is selected
- ✅ **Viewer Toolbar** with viewer selection
- ✅ **Status Handling** (ready, processing, unsupported, error)
- ✅ **Multiple Viewers** (OpenVisus, Bokeh, Jupyter, Plotly, VTK)

### 3. **Right Sidebar - Dataset Details**
- ✅ **Dataset Information** (UUID, size, status, sensor)
- ✅ **Action Buttons** (View, Share, Delete)
- ✅ **Metadata Display** (creation date, dimensions)
- ✅ **Responsive Design** (collapsible sidebar)

### 4. **Interactive Features**
- ✅ **Theme Toggle** (dark/light mode)
- ✅ **Dataset Selection** (click on dataset names)
- ✅ **Sidebar Controls** (collapse/expand)
- ✅ **Viewer Switching** (change viewer type)
- ✅ **Responsive Design** (mobile-friendly)

## 🔧 Test Scenarios

### Scenario 1: Basic Navigation
1. Open http://localhost:8000/test-index.php
2. Click on "My Datasets" to expand
3. Click on "Sample Dataset 1" to select it
4. Verify details appear in right sidebar
5. Verify dashboard loads in main area

### Scenario 2: Viewer Switching
1. Select a dataset
2. Change viewer type in toolbar dropdown
3. Verify dashboard updates
4. Test all viewer types (OpenVisus, Bokeh, Jupyter, Plotly, VTK)

### Scenario 3: Responsive Design
1. Resize browser window
2. Test sidebar collapse/expand
3. Test mobile view (use browser dev tools)
4. Verify theme toggle works

### Scenario 4: API Testing
Test the API endpoints directly:
- **GET** http://localhost:8000/api/datasets.php
- **GET** http://localhost:8000/api/dataset-details.php?dataset_id=507f1f77bcf86cd799439012
- **GET** http://localhost:8000/api/dataset-status.php?dataset_id=507f1f77bcf86cd799439012

## 📊 Mock Data

The test environment includes:

### Sample Datasets:
1. **Sample Dataset 1** (TIFF, done, 1MB)
2. **Sample Dataset 2** (HDF5, processing, 2MB)

### Sample User:
- **Name**: Test User
- **Email**: test@example.com
- **ID**: 507f1f77bcf86cd799439011
- **Permissions**: read, upload

### Sample Folders:
- **Folder 1**: 1 dataset
- **Folder 2**: 1 dataset

## 🐛 Troubleshooting

### Common Issues:

1. **"Page not found" errors**
   - Make sure you're using the correct URL: http://localhost:8000/test-index.php
   - Check that the PHP server is running

2. **JavaScript errors**
   - Open browser developer tools (F12)
   - Check Console tab for errors
   - Verify all files are loading correctly

3. **CSS not loading**
   - Check that assets/css/main.css exists
   - Verify file permissions

4. **PHP errors**
   - Check the PHP test script: http://localhost:8000/test-php.php
   - Look for error messages in the output

### Debug Mode:
- Open browser developer tools (F12)
- Check Console for JavaScript errors
- Check Network tab for failed requests
- Check Elements tab for HTML structure

## 🔄 Development Workflow

### Making Changes:
1. Edit files in your IDE
2. Refresh browser to see changes
3. Check console for errors
4. Test functionality

### Adding New Features:
1. Create new PHP files in appropriate directories
2. Update JavaScript modules
3. Test with mock data
4. Verify integration

### Testing Real Data:
1. Replace mock functions with real scientistCloudLib calls
2. Configure real MongoDB connection
3. Set up real authentication
4. Test with actual datasets

## 📝 Test Checklist

- [ ] Website loads without errors
- [ ] Left sidebar shows datasets
- [ ] Dataset selection works
- [ ] Right sidebar shows details
- [ ] Viewer switching works
- [ ] Theme toggle works
- [ ] Responsive design works
- [ ] API endpoints return data
- [ ] No JavaScript errors in console
- [ ] No PHP errors in output

## 🚀 Next Steps

1. **Test with Real Data**: Replace mock functions with real scientistCloudLib integration
2. **Authentication**: Implement real Auth0 authentication
3. **Database**: Connect to real MongoDB instance
4. **Deployment**: Deploy to production server
5. **User Testing**: Get feedback from actual users

## 📞 Support

If you encounter issues:
1. Check the PHP test script output
2. Review browser console for errors
3. Verify all files are in the correct locations
4. Check file permissions
5. Ensure PHP server is running on port 8000
