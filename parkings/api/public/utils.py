def blur_count(count, threshold=3):
    """
    Returns a blurred count, which is supposed to hide individual
    parkings.
    """
    if count <= threshold:
        return 0
    else:
        return count
