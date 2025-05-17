import cv2
import os
import numpy as np
import json


def remove_text_from_image(image_path):
    import cv2
import numpy as np
import os

def remove_text_from_image(image_path):
    """
    Enhanced text removal function for floor plans that better distinguishes
    between walls and text elements.
    """
    # Load the image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image from {image_path}")
    
    # Create a copy for results
    result_img = img.copy()
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Create debug directory
    debug_dir = os.path.dirname(image_path)
    
    # Step 1: Apply adaptive thresholding to better identify text elements
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV, 11, 2)
                                  
    # Save thresholded image for debugging
    cv2.imwrite(os.path.join(debug_dir, "threshold.png"), thresh)
    
    # Step 2: Perform morphological operations to isolate text-like components
    # Text typically has smaller components than walls
    
    # Create a kernel for text isolation - smaller than wall thickness
    text_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    
    # Open operation to remove small connections and noise
    text_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, text_kernel, iterations=1)
    
    # Close operation to connect characters within text
    text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, text_kernel, iterations=1)
    
    # Save text mask for debugging
    cv2.imwrite(os.path.join(debug_dir, "text_mask.png"), text_mask)
    
    # Step 3: Create a separate mask for identifying walls
    # Walls are typically thicker and have longer continuous lines
    
    # Create a kernel for wall isolation - larger than text components
    wall_kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))  # Horizontal walls
    wall_kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))  # Vertical walls
    
    # Detect horizontal walls
    horizontal_walls = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, wall_kernel_h, iterations=1)
    
    # Detect vertical walls
    vertical_walls = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, wall_kernel_v, iterations=1)
    
    # Combine horizontal and vertical walls
    walls_mask = cv2.bitwise_or(horizontal_walls, vertical_walls)
    
    # Save walls mask for debugging
    cv2.imwrite(os.path.join(debug_dir, "wall_mask.png"), walls_mask)
    
    # Step 4: Find text components that aren't part of walls
    # Text is what remains in text_mask but not in walls_mask
    text_only = cv2.bitwise_and(text_mask, cv2.bitwise_not(walls_mask))
    
    # Save text only mask for debugging
    cv2.imwrite(os.path.join(debug_dir, "text_only.png"), text_only)
    
    # Step 5: Find contours in the text-only mask
    contours, _ = cv2.findContours(text_only, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Step 6: Filter contours based on size and aspect ratio to identify text components
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h) if h > 0 else 0
        area = cv2.contourArea(cnt)
        
        # Text typically has small area and specific aspect ratio ranges
        # Fine-tune these parameters based on your blueprints
        is_text = (area < 500 and 
                  (0.5 < aspect_ratio < 15 or  # For normal text
                   aspect_ratio < 0.5))  # For vertical text like 'CLOSET'
        
        if is_text:
            # Paint over text with white (or background color)
            cv2.rectangle(result_img, (x, y), (x + w, y + h), (255, 255, 255), -1)
    
    # Step 7: Additional pass for dimensions text which often has specific patterns
    # Look for text near walls that resembles dimensions (e.g., "12' x 10'")
    lower_text = gray.copy()
    
    # Apply a more aggressive threshold to catch dimension text
    _, dim_thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    
    # Dilate to connect nearby characters in dimension text
    dim_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dim_text = cv2.dilate(dim_thresh, dim_kernel, iterations=1)
    
    # Find contours for dimension text
    dim_contours, _ = cv2.findContours(dim_text, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in dim_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = w / float(h) if h > 0 else 0
        area = cv2.contourArea(cnt)
        
        # Dimensions text typically has specific characteristics
        is_dim_text = (area < 1000 and area > 50 and 
                      (1.5 < aspect_ratio < 10 or  # For horizontal dimensions
                       aspect_ratio < 0.7))        # For vertical dimensions
        
        if is_dim_text:
            # Check if this overlaps with any previously identified wall
            region = walls_mask[y:y+h, x:x+w]
            if np.sum(region) < 0.5 * w * h * 255:  # Less than 50% overlap with walls
                cv2.rectangle(result_img, (x, y), (x + w, y + h), (255, 255, 255), -1)
    
    # Save the result for debugging
    cv2.imwrite(os.path.join(debug_dir, "text_removed_result.png"), result_img)
    
    return result_img


def process_blueprint_image(file_path):
    """
    Process blueprint image to detect walls and extract their coordinates.
    Specifically designed for floor plans with black lines representing walls.
    """
    print(f"Processing file: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Load image
    original = cv2.imread(file_path)
    if original is None:
        raise ValueError(f"Image at {file_path} could not be loaded. Make sure it's a PNG or JPEG.")
    
    # Create a copy for visualization
    vis_image = original.copy()
    
    # Convert to grayscale
    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    
    # Threshold to isolate black lines (walls)
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    
    # Create a debug image to save intermediate results
    debug_binary = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    
    # Find line segments using Hough Line Transform
    # For precise wall detection in blueprints, we'll identify line segments and then group them
    edges = cv2.Canny(binary, 50, 150, apertureSize=3)
    
    # Use probabilistic Hough transform to detect line segments
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=50, maxLineGap=10)
    
    # Create a new image to draw the detected lines for visualization
    line_image = np.zeros_like(original)
    
    # Process detected lines and store wall segments
    wall_segments = []
    if lines is not None:
        for i, line in enumerate(lines):
            x1, y1, x2, y2 = line[0]
            # Draw the line on the visualization image
            cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Store wall segment data
            wall_segments.append({
                "id": f"segment_{i}",
                "start": [int(x1), int(y1)],
                "end": [int(x2), int(y2)],
                "length": np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            })
    
    # Create a mask of walls by dilating the line segments
    wall_mask = np.zeros_like(gray)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(wall_mask, (x1, y1), (x2, y2), 255, 5)  # Thicker line for better detection
    
    # Dilate the mask to connect nearby wall segments
    kernel = np.ones((5, 5), np.uint8)
    wall_mask = cv2.dilate(wall_mask, kernel, iterations=1)
    
    # Save the wall mask for debugging
    debug_dir = os.path.dirname(file_path)
    cv2.imwrite(os.path.join(debug_dir, "wall_mask.png"), wall_mask)
    
    # Find contours on the wall mask to identify room boundaries
    contours, _ = cv2.findContours(wall_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Process room boundaries
    rooms = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < 1000:  # Skip very small contours
            continue
            
        # Simplify the room polygon
        epsilon = 0.01 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # Extract room boundary points
        points = approx.reshape(-1, 2).tolist()
        
        # Add room data
        rooms.append({
            "id": f"room_{i}",
            "polygon": points,
            "area": area
        })
        
        # Draw room boundary on visualization
        cv2.drawContours(vis_image, [approx], 0, (0, 0, 255), 2)
    
    # Detect individual walls using a different approach
    # We'll use horizontal and vertical kernel matching to detect wall sections
    
    # Morphological operations to isolate walls
    kernel_h = np.ones((1, 15), np.uint8)  # Horizontal kernel
    kernel_v = np.ones((15, 1), np.uint8)  # Vertical kernel
    
    # Extract horizontal and vertical components
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_h)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_v)
    
    # Combine horizontal and vertical components
    wall_lines = cv2.bitwise_or(horizontal, vertical)
    
    # Dilate to connect components
    wall_lines = cv2.dilate(wall_lines, np.ones((3, 3), np.uint8), iterations=1)
    
    # Save wall lines for debugging
    cv2.imwrite(os.path.join(debug_dir, "wall_lines.png"), wall_lines)
    
    # Find contours of wall sections
    wall_contours, _ = cv2.findContours(wall_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Process wall sections
    walls = []
    for i, cnt in enumerate(wall_contours):
        area = cv2.contourArea(cnt)
        if area < 100:  # Skip very small contours
            continue
            
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Determine if horizontal or vertical wall
        is_horizontal = w > h
        
        # Simplify the wall polygon
        epsilon = 0.01 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # Extract wall points
        points = approx.reshape(-1, 2).tolist()
        
        # Add wall data
        wall_type = "horizontal" if is_horizontal else "vertical"
        walls.append({
            "id": f"wall_{i}",
            "type": wall_type,
            "polygon": points,
            "area": area,
            "bounds": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            }
        })
        
        # Draw wall on visualization
        color = (0, 255, 0) if is_horizontal else (255, 0, 0)
        cv2.drawContours(vis_image, [approx], 0, color, 2)
        
        # Add wall ID text
        cv2.putText(vis_image, f"wall_{i}", (x + w//2 - 20, y + h//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    # Save the visualization image
    debug_path = os.path.join(debug_dir, f"debug_{os.path.basename(file_path)}")
    cv2.imwrite(debug_path, vis_image)
    
    # Save lines visualization
    cv2.imwrite(os.path.join(debug_dir, "detected_lines.png"), line_image)
    
    # Combine horizontal and vertical wall detection for final result
    combined_vis = cv2.addWeighted(original, 0.7, line_image, 0.3, 0)
    cv2.imwrite(os.path.join(debug_dir, "combined_detection.png"), combined_vis)
    
    return {
        "walls": walls,
        "wall_segments": wall_segments,
        "rooms": rooms,
        "image_dimensions": {
            "width": original.shape[1],
            "height": original.shape[0]
        }
    }

def reconstruct_blueprint(json_path, output_path="reconstructed_blueprint.png", canvas_size=None):
    """
    Reconstruct blueprint from JSON data with improved visualization.
    """
    # Load the JSON blueprint data
    with open(json_path, 'r') as file:
        blueprint = json.load(file)
    
    # Get image dimensions from JSON or use default
    if "image_dimensions" in blueprint["data"]:
        width = blueprint["data"]["image_dimensions"]["width"]
        height = blueprint["data"]["image_dimensions"]["height"]
        canvas_size = (width, height)
    elif canvas_size is None:
        canvas_size = (1600, 1200)
    
    # Create a blank white canvas
    canvas = np.ones((canvas_size[1], canvas_size[0], 3), dtype=np.uint8) * 255
    
    # Draw wall segments if available
    if "wall_segments" in blueprint["data"]:
        for segment in blueprint["data"]["wall_segments"]:
            start = tuple(segment["start"])
            end = tuple(segment["end"])
            cv2.line(canvas, start, end, (0, 0, 0), 2)
    
    # Draw walls with different colors
    if "walls" in blueprint["data"]:
        for wall in blueprint["data"]["walls"]:
            if len(wall["polygon"]) < 3:  # Skip invalid polygons
                continue
                
            # Convert points to numpy array
            polygon = np.array(wall["polygon"], dtype=np.int32)
            polygon = polygon.reshape((-1, 1, 2))
            
            # Choose color based on wall type
            if wall.get("type") == "horizontal":
                color = (0, 0, 255)  # Red for horizontal walls
            else:
                color = (255, 0, 0)  # Blue for vertical walls
            
            # Draw filled polygon with transparency
            filled = canvas.copy()
            cv2.fillPoly(filled, [polygon], color=color)
            cv2.addWeighted(filled, 0.3, canvas, 0.7, 0, canvas)
            
            # Draw outline
            cv2.polylines(
                canvas, 
                [polygon], 
                isClosed=True, 
                color=(0, 0, 0), 
                thickness=1
            )
            
            # Add wall ID text
            if "bounds" in wall:
                x = wall["bounds"]["x"]
                y = wall["bounds"]["y"]
                w = wall["bounds"]["width"]
                h = wall["bounds"]["height"]
                cv2.putText(
                    canvas, 
                    wall["id"], 
                    (x + w//2 - 20, y + h//2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.4, 
                    (0, 0, 0), 
                    1
                )
    
    # Draw room boundaries if available
    if "rooms" in blueprint["data"]:
        for room in blueprint["data"]["rooms"]:
            if len(room["polygon"]) < 3:  # Skip invalid polygons
                continue
                
            # Convert points to numpy array
            polygon = np.array(room["polygon"], dtype=np.int32)
            polygon = polygon.reshape((-1, 1, 2))
            
            # Draw room boundary
            cv2.polylines(
                canvas, 
                [polygon], 
                isClosed=True, 
                color=(0, 255, 0), 
                thickness=1
            )
    
    # Save the reconstructed blueprint
    cv2.imwrite(output_path, canvas)
    print(f"Reconstructed blueprint saved to: {output_path}")
    
    return canvas

def extract_individual_walls(file_path):
    """
    Alternative approach to extract individual walls from the blueprint
    by detecting black lines directly from the image.
    """
    image = cv2.imread(file_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Threshold to get black lines
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter and process wall contours
    walls = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < 50:  # Skip very small contours
            continue
        
        # Get bounding rect to determine if horizontal or vertical
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Determine if it's likely a wall
        aspect_ratio = float(w) / h if h > 0 else 0
        is_wall = (aspect_ratio > 5 or aspect_ratio < 0.2) and min(w, h) < 20
        
        if is_wall:
            # Simplify the wall polygon
            epsilon = 0.01 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            # Extract wall points
            points = approx.reshape(-1, 2).tolist()
            
            # Add wall data
            wall_type = "horizontal" if w > h else "vertical"
            walls.append({
                "id": f"wall_{i}",
                "type": wall_type,
                "polygon": points,
                "area": area,
                "bounds": {
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h)
                }
            })
    
    return walls