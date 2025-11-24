"""
Temporal Normalization Utility
Merges adjacent segments from the same speaker and normalizes timestamps.
"""

def normalize_temporal_segments(segments, merge_threshold=0.5):
    """
    Normalize timestamps and merge adjacent segments from same speaker.
    
    Args:
        segments: List of segments with start, end, speaker, text
        merge_threshold: Time gap threshold for merging (seconds)
    
    Returns:
        normalized_segments: Merged and normalized segments
    """
    if not segments:
        return []
    
    normalized = []
    current_seg = None
    
    for seg in segments:
        if current_seg is None:
            current_seg = seg.copy()
            continue
        
        # Check if same speaker and gap is small enough to merge
        same_speaker = current_seg.get("speaker") == seg.get("speaker")
        gap = seg["start"] - current_seg["end"]
        
        if same_speaker and gap <= merge_threshold:
            # Merge segments
            current_seg["end"] = seg["end"]
            current_seg["text"] = current_seg["text"] + " " + seg["text"]
        else:
            # Save current segment and start new one
            normalized.append(current_seg)
            current_seg = seg.copy()
    
    # Don't forget the last segment
    if current_seg is not None:
        normalized.append(current_seg)
    
    return normalized

