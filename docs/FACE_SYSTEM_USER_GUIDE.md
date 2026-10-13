# Face Recognition System User Guide

**Version**: 2.0
**Date**: December 25, 2025
**Audience**: End Users & Administrators

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding Face Recognition](#understanding-face-recognition)
3. [Managing People](#managing-people)
4. [Advanced Search](#advanced-search)
5. [Photo Detail Integration](#photo-detail-integration)
6. [Performance & Optimization](#performance--optimization)
7. [Privacy & Security](#privacy--security)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Initial Setup

1. **First Scan**: Navigate to the People page and click "Scan for Faces"
2. **Wait for Processing**: The system will analyze your photos and group faces
3. **Review Results**: Check the automatically created people clusters
4. **Add Names**: Click on clusters to add names for people you recognize

### Understanding the Interface

The People page shows:
- **Cluster Cards**: Each card represents one person
- **Face Count**: Number of face detections for this person
- **Quality Indicators**: Color-coded badges showing cluster quality
- **Action Buttons**: Quick access to management functions

---

## Understanding Face Recognition

### How We Identify People

Our system uses advanced computer vision to:
1. **Detect Faces**: Find faces in your photos and videos
2. **Extract Features**: Create unique "fingerprints" for each face
3. **Group Similar Faces**: Cluster faces that likely belong to the same person
4. **Learn Over Time**: Improve accuracy as you provide feedback

### Quality Indicators

Each person cluster shows a quality badge:
- 🟢 **High Quality** (80-100%): Very confident this is one person
- 🟡 **Good Quality** (60-79%): Likely one person, may need review
- 🔴 **Needs Review** (<60%): May contain multiple people

### Confidence Scores

Individual face detections show confidence levels:
- **90-100%**: Very confident face detection
- **80-89%**: Good face detection
- **70-79%**: Acceptable face detection
- **<70%**: Low confidence, may need manual review

---

## Managing People

### Adding Names

1. Click on any unnamed cluster
2. Select "Rename Person" from the menu
3. Enter the person's name
4. Click "Save"

**Tip**: Use consistent naming (e.g., "First Last" format) for better organization.

### Splitting Mixed Clusters

If a cluster contains multiple people:

1. Click the "Split" button on the cluster card
2. Select faces that belong to a different person
3. Enter a name for the new person
4. Click "Create New Person"

The selected faces will be moved to a new cluster.

### Moving Individual Faces

To move a single face between people:

1. Right-click on a face thumbnail
2. Select "Move to Different Person"
3. Choose the destination person or create a new one
4. Confirm the move

### Merging People

If you have duplicate clusters for the same person:

1. Click "Merge" on one of the clusters
2. Select the target cluster to merge into
3. Confirm the merge operation

**Note**: Merge operations can be undone using the Undo button.

### Hiding People

For privacy or organization:

1. Click the "Hide" button on a cluster
2. The person will be removed from the main view
3. Use "Show Hidden" toggle to manage hidden people
4. Click "Unhide" to restore visibility

---

## Advanced Search

### Boolean People Search

Create complex searches using AND/OR logic:

1. Click "Advanced Search" in the People page header
2. Add people to include or exclude
3. Choose AND (all people must appear) or OR (any people can appear)
4. View matching photos in the results grid

**Examples**:
- "Alice AND Bob": Photos containing both Alice and Bob
- "Alice OR Bob": Photos containing either Alice or Bob
- "Alice NOT Charlie": Photos with Alice but not Charlie

### Similar Face Search

Find faces similar to a specific person:

1. Click on any face thumbnail
2. Select "Find Similar Faces"
3. Adjust the similarity threshold slider
4. Review potential matches
5. Move faces to the correct person if needed

### Photo-Based Search

From any photo detail view:
1. Click on a face in the People section
2. Use the context menu for quick actions
3. Find similar faces across your entire library

---

## Photo Detail Integration

### Face Management in Photos

When viewing a photo, the People section shows:
- **Detected People**: All people found in this photo
- **Face Thumbnails**: Cropped face images with quality indicators
- **Quick Actions**: Context menu for each person

### Available Actions

Right-click on any face for options:
- **View All Photos**: See all photos of this person
- **Find Similar Faces**: Discover similar faces
- **Rename Person**: Change the person's name
- **Hide Person**: Remove from main gallery

### Video Face Tracking

For videos, the system provides:
- **Temporal Tracking**: Follows faces across video frames
- **Best Frame Selection**: Shows the clearest face image
- **Timeline Navigation**: Jump to specific appearances

---

## Performance & Optimization

### System Performance

The system automatically optimizes for your collection size:

- **Small Collections** (<1,000 faces): Uses Linear search for speed
- **Large Collections** (≥1,000 faces): Automatically upgrades to FAISS for scalability

### Cache Management

Face images are cached for instant loading:
- **Cache Hit Rate**: Aim for >80% for optimal performance
- **Cache Size**: Default 500MB, adjustable in settings
- **Auto-Cleanup**: Old entries automatically removed

### Database Optimization

The system maintains optimal database performance:
- **Automatic Indexing**: Creates indexes for fast queries
- **Regular Maintenance**: Runs optimization tasks in background
- **Performance Monitoring**: Tracks query speeds and system health

### Performance Tips

1. **Regular Scans**: Run face scans after adding new photos
2. **Name People**: Named clusters perform better in searches
3. **Review Quality**: Address low-quality clusters for better accuracy
4. **Clean Up**: Remove or merge duplicate clusters

---

## Privacy & Security

### Data Protection

- **Local Processing**: All face recognition happens on your device
- **No Cloud Upload**: Face data never leaves your system
- **Encrypted Storage**: Face embeddings stored securely

### Privacy Controls

- **Hide People**: Remove sensitive individuals from view
- **Delete Clusters**: Permanently remove face data
- **Undo Operations**: Reverse accidental changes
- **Export Control**: Choose what data to include in exports

### Access Control

- **User Permissions**: Control who can modify face data
- **Audit Trail**: Track all face management operations
- **Backup Options**: Export face data for backup purposes

---

## Troubleshooting

### Common Issues

#### "No Faces Detected"
- **Cause**: Photos may have very small or unclear faces
- **Solution**: Check photo quality and lighting
- **Tip**: Faces should be at least 50x50 pixels for detection

#### "Poor Clustering Quality"
- **Cause**: Similar-looking people or varied lighting conditions
- **Solution**: Use Split Cluster feature to separate people
- **Prevention**: Provide feedback by moving faces to correct clusters

#### "Slow Performance"
- **Cause**: Large collection without optimization
- **Solution**: Run database optimization from settings
- **Check**: Cache hit rate and system health metrics

#### "Missing People in Search"
- **Cause**: Person may be hidden or in low-quality cluster
- **Solution**: Check hidden people and review cluster quality
- **Tip**: Use "Show Hidden" toggle to see all people

### Performance Issues

#### High Memory Usage
1. Check cache size in settings
2. Clear cache if needed
3. Reduce cache size limit
4. Restart application if necessary

#### Slow Face Detection
1. Reduce scan batch size
2. Check available system resources
3. Close other resource-intensive applications
4. Consider upgrading hardware for large collections

### Error Recovery

#### Accidental Operations
- Use the **Undo** button to reverse recent changes
- Check operation history for details
- Contact support if undo doesn't resolve the issue

#### Database Issues
1. Run database optimization
2. Check disk space availability
3. Restart the application
4. Contact support for persistent issues

---

## Advanced Features

### Batch Operations

Process multiple people at once:
- **Bulk Hide**: Select multiple clusters and hide them
- **Batch Rename**: Use consistent naming patterns
- **Mass Export**: Export data for multiple people

### Integration Features

- **Photo Workflows**: Seamless integration with photo editing
- **Search Integration**: People search within global photo search
- **Export Options**: Include face data in photo exports

### API Access

For developers and advanced users:
- **REST API**: Full programmatic access to face features
- **Webhooks**: Real-time notifications for face events
- **Bulk Import**: Import face data from other systems

---

## Best Practices

### Organization

1. **Consistent Naming**: Use "First Last" format for names
2. **Regular Reviews**: Check and improve cluster quality monthly
3. **Prompt Labeling**: Name people as soon as they're detected
4. **Quality Maintenance**: Address mixed clusters quickly

### Performance

1. **Incremental Scans**: Scan new photos regularly rather than large batches
2. **Cache Monitoring**: Keep cache hit rate above 80%
3. **Database Health**: Run optimization monthly for large collections
4. **Resource Management**: Monitor system resources during processing

### Privacy

1. **Review Visibility**: Regularly check who has access to face data
2. **Hide Sensitive People**: Use privacy controls for sensitive individuals
3. **Backup Strategy**: Export important face data regularly
4. **Access Logs**: Monitor who accesses face recognition features

---

## Getting Help

### Documentation
- **API Reference**: Complete technical documentation
- **Video Tutorials**: Step-by-step visual guides
- **FAQ**: Common questions and answers

### Support Channels
- **In-App Help**: Context-sensitive help within the application
- **Community Forum**: User community and discussions
- **Technical Support**: Direct support for technical issues

### Feedback
- **Feature Requests**: Suggest new face recognition features
- **Bug Reports**: Report issues with detailed information
- **Performance Feedback**: Share performance optimization suggestions

---

## Appendix

### Keyboard Shortcuts

- **Ctrl/Cmd + F**: Open face search
- **Ctrl/Cmd + Z**: Undo last operation
- **Space**: Quick preview of selected cluster
- **Enter**: Rename selected cluster
- **Delete**: Hide selected cluster

### File Formats Supported

**Images**: JPG, PNG, HEIC, TIFF, BMP, WebP
**Videos**: MP4, MOV, AVI, MKV, WebM
**RAW Formats**: CR2, NEF, ARW, DNG, and others

### System Requirements

**Minimum**:
- 4GB RAM
- 2GB free disk space
- Modern web browser

**Recommended**:
- 8GB+ RAM for large collections
- SSD storage for better performance
- Dedicated GPU for video processing

---

**Last Updated**: December 25, 2025
**Version**: 2.0
**Next Update**: January 2026
