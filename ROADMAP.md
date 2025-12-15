# PhotoSearch Roadmap

## Pricing Implementation Plan

### Phase 1: Backend Infrastructure (Current Focus)
- [ ] Create pricing logic and tiers in backend
- [ ] Implement image count tracking in database
- [ ] Create API endpoints for usage checking
- [ ] Add user authentication system
- [ ] Implement usage limits and enforcement

### Phase 2: UI Implementation (Future)
- [ ] Create landing page with pricing information
- [ ] Add pricing slider component
- [ ] Implement subscription management UI
- [ ] Add usage dashboard for users
- [ ] Create admin dashboard for monitoring

### Phase 3: Billing Integration
- [ ] Integrate with payment gateway (Stripe, etc.)
- [ ] Implement subscription management
- [ ] Add invoice generation
- [ ] Implement trial periods and discounts

## Pricing Tiers (Proposed)

Based on the discussion about charging by image count:

| Tier | Image Limit | Price | Features |
|------|------------|-------|----------|
| Free | 5,000 | $0 | Basic search, limited features |
| Basic | 25,000 | $9.99/month | Full features, priority support |
| Pro | 100,000 | $29.99/month | Advanced analytics, API access |
| Enterprise | Custom | Custom | Custom solutions, dedicated support |

## Technical Implementation

### Database Changes
- Add `users` table for user management
- Add `usage` table to track image counts per user
- Add `subscriptions` table for billing information
- Add `pricing_tiers` table for flexible tier management

### API Endpoints
- `GET /pricing` - Get available pricing tiers
- `GET /usage` - Get current usage statistics
- `POST /subscribe` - Subscribe to a plan
- `GET /billing` - Get billing information

### Backend Logic
- Usage tracking middleware
- Rate limiting based on tier
- Feature access control
- Billing cycle management

## Search UX Enhancements (Recently Implemented)

### ✅ Week 1 High-Priority Features (Completed)
- [x] **Intent Recognition Integration** - Auto-mode switching based on detected user intent
- [x] **Live Match Count** - Real-time feedback while typing with debounced API calls
- [x] **Field Autocomplete for Metadata Mode** - Smart suggestions for technical queries
- [x] **Match Explanations** - Detailed "Why?" breakdowns with proper modal positioning

### ✅ Granular Match Scoring Breakdown (CRITICAL NEW FEATURE)
- [x] **Color-coded Score Display**: `File: 80% | Content: 25%` with visual indicators
- [x] **Transparency Features**: Users see exactly what matched and why
- [x] **Score Categories**: File, Content, Metadata, Semantic with emoji icons
- [x] **Realistic Scoring**: Prevented inflated matches for irrelevant content
- [x] **Living Application Language**: "We found/identified" instead of "AI detected"

### 🎯 Search UX Design Philosophy
- **User Mental Model First**: Semantic search default (users expect "people" to find people, not filenames)
- **Score-Based Relevance**: Sort by combined relevance scores, not search mode priority
- **Trust Through Transparency**: Detailed explanations build user confidence
- **Professional Workflow**: Modal explanations don't interfere with photo browsing

## Future Search Enhancements

### Phase 1: Intelligence & Personalization
- [ ] **Machine Learning Personalization** - Learn from user click patterns and preferences
- [ ] **Advanced Intent Detection** - More sophisticated query analysis and context understanding
- [ ] **Search Analytics Dashboard** - Track search performance and user behavior patterns
- [ ] **Query Suggestions** - Smart autocomplete based on user history and popular searches

### Phase 2: Visual & Multimodal Search
- [ ] **Visual Similarity Search** - Image-to-image search capabilities with drag-and-drop
- [ ] **Reverse Image Search** - Find similar photos by uploading or selecting reference images
- [ ] **Color-based Search** - Find photos by dominant colors or color palettes
- [ ] **Composition Analysis** - Search by visual composition (rule of thirds, symmetry, etc.)

### Phase 3: Advanced Features
- [ ] **Collaborative Filtering** - "Users who searched for X also found Y" recommendations
- [ ] **Saved Search Collections** - Save and organize frequently used search queries
- [ ] **Search History Analytics** - Personal insights into search patterns and photo discovery
- [ ] **Batch Operations from Search** - Select and process multiple search results

### Phase 4: Professional Tools
- [ ] **Custom Metadata Fields** - User-defined searchable metadata categories
- [ ] **Advanced Boolean Queries** - Complex search logic with AND/OR/NOT operators
- [ ] **Search API for Integrations** - RESTful API for third-party applications
- [ ] **Bulk Metadata Editing** - Edit metadata for multiple search results simultaneously

## Pricing & Business Features

### Phase 1: Backend Infrastructure (Current Focus)
- [ ] Create pricing logic and tiers in backend
- [ ] Implement image count tracking in database
- [ ] Create API endpoints for usage checking
- [ ] Add user authentication system
- [ ] Implement usage limits and enforcement

### Phase 2: UI Implementation (Future)
- [ ] Create landing page with pricing information
- [ ] Add pricing slider component
- [ ] Implement subscription management UI
- [ ] Add usage dashboard for users
- [ ] Create admin dashboard for monitoring

### Phase 3: Billing Integration
- [ ] Integrate with payment gateway (Stripe, etc.)
- [ ] Implement subscription management
- [ ] Add invoice generation
- [ ] Implement trial periods and discounts

## Pricing Tiers (Proposed)

Based on the discussion about charging by image count:

| Tier | Image Limit | Price | Features |
|------|------------|-------|----------|
| Free | 5,000 | $0 | Basic search, limited features |
| Basic | 25,000 | $9.99/month | Full features, priority support |
| Pro | 100,000 | $29.99/month | Advanced analytics, API access |
| Enterprise | Custom | Custom | Custom solutions, dedicated support |

## Technical Implementation

### Database Changes
- Add `users` table for user management
- Add `usage` table to track image counts per user
- Add `subscriptions` table for billing information
- Add `pricing_tiers` table for flexible tier management

### API Endpoints
- `GET /pricing` - Get available pricing tiers
- `GET /usage` - Get current usage statistics
- `POST /subscribe` - Subscribe to a plan
- `GET /billing` - Get billing information

### Backend Logic
- Usage tracking middleware
- Rate limiting based on tier
- Feature access control
- Billing cycle management

## Future Business Enhancements
- Team/collaboration features
- Multi-user accounts
- Usage analytics and reporting
- Custom pricing for enterprise customers