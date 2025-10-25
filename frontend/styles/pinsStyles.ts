import { StyleSheet } from 'react-native';

export const pinsStyles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#fff',
    paddingBottom: 120 // Add padding for floating tab bar
  },
  safeAreaBanner: { 
    height: 50, 
    backgroundColor: '#fff' 
  },
  
  // Filter UI Styles
  filterContainer: {
    backgroundColor: '#f8f9fa',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  filterTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: '#333',
  },
  filterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  filterSection: {
    flex: 1,
    marginRight: 8,
  },
  filterSectionTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
    color: '#555',
  },
  categoryFilterContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  categoryChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
  },
  categoryChipSelected: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  categoryChipText: {
    fontSize: 12,
    color: '#666',
    textTransform: 'capitalize',
  },
  categoryChipTextSelected: {
    color: '#fff',
  },
  distanceFilterContainer: {
    flex: 1,
    marginLeft: 8,
  },
  distanceSlider: {
    height: 40,
  },
  distanceText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 4,
  },
  clearFiltersButton: {
    alignSelf: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#ff6b6b',
    borderRadius: 16,
    marginTop: 8,
  },
  clearFiltersText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  filteredResultsText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 8,
    fontStyle: 'italic',
  },
  
  // Sort Popup Styles
  sortPopupContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  sortPopupContent: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 20,
    margin: 20,
    minWidth: 200,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  sortPopupTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
    textAlign: 'center',
    color: '#333',
  },
  sortOptionsColumn: {
    gap: 8,
  },
  sortPopupOption: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: '#f8f9fa',
    borderWidth: 1,
    borderColor: '#e9ecef',
  },
  sortPopupOptionActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  sortPopupOptionText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    textAlign: 'center',
  },
  sortPopupOptionTextActive: {
    color: '#fff',
  },
  locationWarning: {
    fontSize: 12,
    color: '#ff6b6b',
    marginTop: 12,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  
  center: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center', 
    padding: 16 
  },
  loadingText: { 
    marginTop: 12, 
    fontSize: 16 
  },
  errorText: { 
    fontSize: 16, 
    color: 'crimson', 
    textAlign: 'center', 
    marginBottom: 4 
  },
  helper: { 
    fontSize: 12, 
    color: '#666' 
  },
  emptyContainer: { 
    flexGrow: 1, 
    justifyContent: 'center', 
    alignItems: 'center', 
    padding: 24 
  },
  emptyText: { 
    fontSize: 16, 
    color: '#555' 
  },
  itemContainer: { 
    marginHorizontal: 12, 
    marginVertical: 8, 
    padding: 14, 
    borderRadius: 10, 
    shadowColor: '#000', 
    shadowOpacity: 0.05, 
    shadowRadius: 4, 
    elevation: 2 
  },
  itemHeaderRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    marginBottom: 4 
  },
  category: { 
    fontWeight: '600', 
    fontSize: 15, 
    textTransform: 'capitalize' 
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 4,
    marginBottom: 2,
    color: '#333',
  },
  timestamp: { 
    fontSize: 11, 
    color: '#666' 
  },
  description: { 
    marginTop: 2, 
    fontSize: 14 
  },
  coords: { 
    marginTop: 6, 
    fontSize: 12, 
    color: '#333' 
  },
  distance: { 
    marginTop: 4, 
    fontSize: 12, 
    color: '#007AFF', 
    fontWeight: '500' 
  },
  owner: { 
    marginTop: 4, 
    fontSize: 11, 
    color: '#777' 
  },
  tapHint: { 
    marginTop: 6, 
    fontSize: 11, 
    color: '#999', 
    fontStyle: 'italic', 
    textAlign: 'center' 
  },
  categoryBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    alignSelf: 'flex-start'
  },
  categoryBannerText: {
    marginLeft: 6,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5
  },
  
  // New pin item layout styles
  pinHeaderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  categoryCircle: {
    width: 50,
    height: 50,
    borderRadius: 25,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.15,
    shadowRadius: 3,
    elevation: 3,
  },
  pinInfoContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  pinMetaInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 2,
  },
  reactionContainer: {
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    opacity: 0.8,
  },
  
  // Creator info styles
  creatorInfoContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  creatorBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  creatorAvatar: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#f0f0f0',
  },
  creatorAvatarPlaceholder: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  creatorText: {
    fontSize: 11,
    color: '#666',
    fontStyle: 'italic',
  },
});