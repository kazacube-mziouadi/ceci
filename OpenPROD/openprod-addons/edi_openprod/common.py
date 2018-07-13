# -*- coding: utf-8 -*-
def format_path(path): 
    if path and path[-1] != '/':
        path = '%s/'%(path)
    
    return path