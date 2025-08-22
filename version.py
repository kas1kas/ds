import json
import re
import os
import logging

class VersionChecker:
    def __init__(self):
        self.expected_version = None
        
    def get_python_version(self, python_file_path):
        """Extract version from Python file"""
        try:
            with open(python_file_path, 'r', encoding='utf-8') as f:
                logging.info (f" {f}")
                content = f.read()
            
            # Look for __version__ = "x.xx" pattern
            version_pattern = r'__version__\s*=\s*["\']([\d.]+)["\']'
            match = re.search(version_pattern, content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"Error reading Python file: {e}")
        return None
    
    def get_html_version(self, html_file_path):
        """Extract version from HTML file"""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                logging.info (f" {f}")
                content = f.read()
            
            # Look for meta tag or comment pattern
            meta_pattern = r'<meta\s+name=["\']version["\']\s+content=["\']([\d.]+)["\']'
            comment_pattern = r'<!--\s*version:\s*([\d.]+)\s*-->'
            
            match = re.search(meta_pattern, content) or re.search(comment_pattern, content)
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
        return None
    
    def get_json_version(self, json_file_path):
        """Extract version from JSON config file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                logging.info (f" {f}")
                config = json.load(f)
            
            return config.get('VERSION', '').strip()
        except Exception as e:
            print(f"Error reading JSON file: {e}")
        return None
    
    def check_versions(self, python_files, html_files, json_files):
        """Check if all files have the same version"""
        versions = {}
        
        # Collect versions from all files
        for py_file in python_files:
            if os.path.exists(py_file):
                versions[py_file] = self.get_python_version(py_file)
        
        for html_file in html_files:
            if os.path.exists(html_file):
                versions[html_file] = self.get_html_version(html_file)
        
        for json_file in json_files:
            if os.path.exists(json_file):
                versions[json_file] = self.get_json_version(json_file)
        
        # Find the most common version (expected version)
        version_counts = {}
        for version in versions.values():
            if version:
                version_counts[version] = version_counts.get(version, 0) + 1
        
        if version_counts:
            self.expected_version = max(version_counts.items(), key=lambda x: x[1])[0]
        
        # Check for inconsistencies
        inconsistencies = []
        for file_path, version in versions.items():
            if version and version != self.expected_version:
                inconsistencies.append((file_path, version))
        
        return inconsistencies, self.expected_version
    
    def update_versions(self, new_version, python_files, html_files, json_files):
        """Update version in all files"""
        updated_files = []
        
        # Update Python files
        for py_file in python_files:
            if self.update_python_version(py_file, new_version):
                updated_files.append(py_file)
        
        # Update HTML files
        for html_file in html_files:
            if self.update_html_version(html_file, new_version):
                updated_files.append(html_file)
        
        # Update JSON files
        for json_file in json_files:
            if self.update_json_version(json_file, new_version):
                updated_files.append(json_file)
        
        return updated_files
    
    def update_python_version(self, file_path, new_version):
        """Update version in Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace version pattern
            new_content = re.sub(
                r'(__version__\s*=\s*["\'])([\d.]+)(["\'])',
                f'\\g<1>{new_version}\\g<3>',
                content
            )
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
        except Exception as e:
            print(f"Error updating Python file: {e}")
        return False
    
    def update_html_version(self, file_path, new_version):
        """Update version in HTML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update meta tag
            new_content = re.sub(
                r'(<meta\s+name=["\']version["\']\s+content=["\'])([\d.]+)(["\'])',
                f'\\g<1>{new_version}\\g<3>',
                content
            )
            
            # Update comment
            new_content = re.sub(
                r'(<!--\s*Version:\s*)([\d.]+)(\s*-->)',
                f'\\g<1>{new_version}\\g<3>',
                new_content
            )
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
        except Exception as e:
            print(f"Error updating HTML file: {e}")
        return False
    
    def update_json_version(self, file_path, new_version):
        """Update version in JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if config.get('VERSION') != new_version:
                config['VERSION'] = new_version
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                return True
        except Exception as e:
            print(f"Error updating JSON file: {e}")
        return False

if __name__ == "__main__":
    checker = VersionChecker()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # Define file paths
    python_files = ['wk.py'] 
    html_files = ['templates/index.html', 'templates/calibration.html']
    json_files = ['config.json']
    
    # Check versions
    inconsistencies, expected_version = checker.check_versions(python_files, html_files, json_files)
    
    if inconsistencies:
        print("Version inconsistencies found:")
        for file_path, version in inconsistencies:
            print(f"  {file_path}: {version} (expected: {expected_version})")
        
        # Optionally update all to expected version
        #response = input("Update all files to expected version? (y/n): ")
        #if response.lower() == 'y':
        #    updated = checker.update_versions(expected_version, python_files, html_files, json_files)
        #    print(f"Updated files: {updated}")
    else:
        print(f"All files have version: {expected_version}")