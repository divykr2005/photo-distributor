const MAX_EDGE = 2560;
const JPEG_QUALITY = 0.82;

self.onmessage = async (e: MessageEvent) => {
  const { id, file } = e.data;

  try {
    // We attempt to load the image using createImageBitmap with from-image orientation.
    // This automatically applies EXIF rotation (critical for iPhone photos).
    // Note: Safari/Chrome support this well, but HEIC may fail in Chrome/Firefox desktop.
    let bitmap: ImageBitmap;
    try {
      bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch (err) {
      console.warn("createImageBitmap failed (possibly HEIC on unsupported browser), returning original file", err);
      // Fallback: return the original file untouched
      self.postMessage({ id, file });
      return;
    }

    let width = bitmap.width;
    let height = bitmap.height;

    // Calculate new dimensions if it exceeds MAX_EDGE
    if (width > MAX_EDGE || height > MAX_EDGE) {
      if (width > height) {
        height = Math.round((height * MAX_EDGE) / width);
        width = MAX_EDGE;
      } else {
        width = Math.round((width * MAX_EDGE) / height);
        height = MAX_EDGE;
      }
    }

    // Create OffscreenCanvas
    const canvas = new OffscreenCanvas(width, height);
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error("Could not get 2d context on OffscreenCanvas");
    }

    // Draw image onto canvas
    ctx.drawImage(bitmap, 0, 0, width, height);

    // Convert canvas to Blob
    const blob = await canvas.convertToBlob({
      type: 'image/jpeg',
      quality: JPEG_QUALITY
    });

    // We must create a new File object to retain the name, but change extension if needed
    let newFileName = file.name;
    const lowerName = file.name.toLowerCase();
    if (lowerName.endsWith('.heic') || lowerName.endsWith('.heif') || lowerName.endsWith('.png')) {
       newFileName = file.name.substring(0, file.name.lastIndexOf('.')) + '.jpg';
    }

    const compressedFile = new File([blob], newFileName, { type: 'image/jpeg' });

    // Free memory
    bitmap.close();

    self.postMessage({ id, file: compressedFile });

  } catch (error: any) {
    console.error("Worker resizing failed:", error);
    self.postMessage({ id, error: error.message || "Unknown error in worker" });
  }
};
