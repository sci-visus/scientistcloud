#!/usr/bin/env python3
"""
Get dimension from a Nexus file
Reads the nexus file and returns the dimension (1, 2, 3, or 4)
"""

import sys
import h5py
import numpy as np

def get_nexus_dimension(nexus_file_path):
    """
    Get the dimension of a dataset from a Nexus file.
    
    Args:
        nexus_file_path: Path to the .nxs file
        
    Returns:
        int: Dimension (1, 2, 3, or 4) or None if cannot determine
    """
    try:
        with h5py.File(nexus_file_path, 'r') as f:
            # Look for data entries in the nexus file
            # Common paths: entry/data, entry/instrument/detector/data, etc.
            
            def find_data_groups(group, path=''):
                """Recursively find data groups/arrays"""
                data_shapes = []
                for key in group.keys():
                    current_path = f"{path}/{key}" if path else key
                    item = group[key]
                    
                    if isinstance(item, h5py.Dataset):
                        # Found a dataset
                        if item.shape:
                            data_shapes.append(item.shape)
                    elif isinstance(item, h5py.Group):
                        # Recursively search subgroups
                        data_shapes.extend(find_data_groups(item, current_path))
                
                return data_shapes
            
            # Search for data arrays
            data_shapes = find_data_groups(f)
            
            if not data_shapes:
                return None
            
            # Find the largest/most complex data array (likely the main dataset)
            largest_shape = max(data_shapes, key=lambda x: len(x) if x else 0)
            
            if largest_shape:
                dimension = len(largest_shape)
                # Nexus files often have extra dimensions, so cap at 4
                return min(dimension, 4)
            
            return None
            
    except Exception as e:
        print(f"Error reading nexus file: {e}", file=sys.stderr)
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: get_nexus_dimension.py <nexus_file_path>", file=sys.stderr)
        sys.exit(1)
    
    nexus_file = sys.argv[1]
    dimension = get_nexus_dimension(nexus_file)
    
    if dimension:
        print(dimension)
        sys.exit(0)
    else:
        print("Could not determine dimension", file=sys.stderr)
        sys.exit(1)


