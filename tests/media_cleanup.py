"""
Media cleanup and tagging workflow simulation module.

This module simulates the media cleanup process that could be part of the
sol-release workflow, handling media file analysis, tagging, folder state
management, and cleanup operations.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field


class ShotType(Enum):
    """Represents different types of media shots."""
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_THE_SHOULDER = "over_the_shoulder"
    ESTABLISHING = "establishing"
    CUTAWAY = "cutaway"
    B_ROLL = "b_roll"


class MediaCategory(Enum):
    """Represents categories of media content."""
    DIALOGUE = "dialogue"
    ACTION = "action"
    AMBIENT = "ambient"
    MUSIC = "music"
    SFX = "sfx"
    NARRATION = "narration"
    INTERVIEW = "interview"
    MONTAGE = "montage"


@dataclass
class MediaFileMetadata:
    """Represents metadata for an individual media file."""
    
    file_path: str
    file_name: str
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    shot_type: Optional[ShotType] = None
    category: Optional[MediaCategory] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "shot_type": self.shot_type.value if self.shot_type else None,
            "category": self.category.value if self.category else None,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "resolved": self.resolved,
            "notes": self.notes
        }
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaFileMetadata":
        """Create from dictionary."""
        return cls(
            file_path=data.get("file_path", ""),
            file_name=data.get("file_name", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            duration_seconds=data.get("duration_seconds"),
            shot_type=ShotType(data["shot_type"]) if data.get("shot_type") else None,
            category=MediaCategory(data["category"]) if data.get("category") else None,
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            modified_at=data.get("modified_at", datetime.now(timezone.utc).isoformat()),
            resolved=data.get("resolved", False),
            notes=data.get("notes")
        )
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the media file."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def mark_resolved(self, notes: Optional[str] = None) -> None:
        """Mark the file as resolved with optional notes."""
        self.resolved = True
        self.notes = notes or self.notes
        self.modified_at = datetime.now(timezone.utc).isoformat()
    
    def is_ready_for_release(self) -> bool:
        """Check if file is ready for release (resolved and has category)."""
        return self.resolved and self.category is not None


@dataclass
class FolderState:
    """Represents the state of a media folder."""
    
    folder_path: str
    folder_name: str
    total_files: int = 0
    resolved_files: int = 0
    total_size_bytes: int = 0
    last_analyzed: Optional[str] = None
    status: str = "pending"  # pending, in_progress, complete, error
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "folder_path": self.folder_path,
            "folder_name": self.folder_name,
            "total_files": self.total_files,
            "resolved_files": self.resolved_files,
            "total_size_bytes": self.total_size_bytes,
            "last_analyzed": self.last_analyzed,
            "status": self.status,
            "issues": self.issues,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FolderState":
        """Create from dictionary."""
        return cls(
            folder_path=data.get("folder_path", ""),
            folder_name=data.get("folder_name", ""),
            total_files=data.get("total_files", 0),
            resolved_files=data.get("resolved_files", 0),
            total_size_bytes=data.get("total_size_bytes", 0),
            last_analyzed=data.get("last_analyzed"),
            status=data.get("status", "pending"),
            issues=data.get("issues", []),
            metadata=data.get("metadata", {})
        )
    
    @property
    def resolution_percentage(self) -> float:
        """Calculate resolution percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.resolved_files / self.total_files) * 100
    
    def is_complete(self) -> bool:
        """Check if folder processing is complete."""
        return self.status == "complete" and self.total_files > 0 and self.resolved_files == self.total_files
    
    def is_already_done(self) -> bool:
        """Check if folder has already been processed completely."""
        return self.status == "complete" and self.total_files > 0 and self.resolved_files == self.total_files
    
    def add_issue(self, issue: str) -> None:
        """Add an issue to the folder."""
        if issue not in self.issues:
            self.issues.append(issue)


@dataclass
class CleanupReport:
    """Report of cleanup operations performed."""
    
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    files_analyzed: int = 0
    files_resolved: int = 0
    files_rejected: int = 0
    files_deleted: int = 0
    folders_processed: int = 0
    total_size_freed_bytes: int = 0
    issues_found: int = 0
    success: bool = True
    error_message: Optional[str] = None
    folder_states: List[FolderState] = field(default_factory=list)
    file_metadata: List[MediaFileMetadata] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "files_analyzed": self.files_analyzed,
            "files_resolved": self.files_resolved,
            "files_rejected": self.files_rejected,
            "files_deleted": self.files_deleted,
            "folders_processed": self.folders_processed,
            "total_size_freed_bytes": self.total_size_freed_bytes,
            "issues_found": self.issues_found,
            "success": self.success,
            "error_message": self.error_message,
            "folder_states": [fs.to_dict() for fs in self.folder_states],
            "file_metadata": [fm.to_dict() for fm in self.file_metadata]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CleanupReport":
        """Create from dictionary."""
        return cls(
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            files_analyzed=data.get("files_analyzed", 0),
            files_resolved=data.get("files_resolved", 0),
            files_rejected=data.get("files_rejected", 0),
            files_deleted=data.get("files_deleted", 0),
            folders_processed=data.get("folders_processed", 0),
            total_size_freed_bytes=data.get("total_size_freed_bytes", 0),
            issues_found=data.get("issues_found", 0),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            folder_states=[FolderState.from_dict(fs) for fs in data.get("folder_states", [])],
            file_metadata=[MediaFileMetadata.from_dict(fm) for fm in data.get("file_metadata", [])]
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class MediaCleanupProcessor:
    """
    Processes media files for cleanup and tagging.
    
    Simulates the workflow of analyzing media files, tagging them,
    and preparing them for release packaging.
    """
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.files: Dict[str, MediaFileMetadata] = {}
        self.folders: Dict[str, FolderState] = {}
        self.temp_folder = self.base_path / "temp_cleanup"
        self.temp_folder.mkdir(exist_ok=True)
    
    def scan_directory(self, directory: Optional[str] = None) -> int:
        """
        Scan a directory for media files.
        
        Returns the number of files found.
        """
        scan_path = Path(directory) if directory else self.base_path
        media_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.jpg', '.png', '.gif', '.wav', '.mp3', '.m4a'}
        file_count = 0
        
        for file_path in scan_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                stat_info = file_path.stat()
                metadata = MediaFileMetadata(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_size_bytes=stat_info.st_size,
                    created_at=datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                    modified_at=datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                )
                self.files[file_path.name] = metadata
                file_count += 1
                
                # Update folder state
                folder_path = str(file_path.parent)
                if folder_path not in self.folders:
                    self.folders[folder_path] = FolderState(
                        folder_path=folder_path,
                        folder_name=file_path.parent.name
                    )
                self.folders[folder_path].total_files += 1
                self.folders[folder_path].total_size_bytes += metadata.file_size_bytes
        
        return file_count
    
    def analyze_file(self, file_name: str) -> Optional[MediaFileMetadata]:
        """Analyze a media file and suggest tags/categories."""
        if file_name not in self.files:
            return None
        
        metadata = self.files[file_name]
        file_lower = file_name.lower()
        
        # Suggest shot type based on filename patterns
        if 'wide' in file_lower or 'establishing' in file_lower:
            metadata.shot_type = ShotType.WIDE
        elif 'closeup' in file_lower or 'cu' in file_lower:
            metadata.shot_type = ShotType.CLOSE_UP
        elif 'cutaway' in file_lower or 'broll' in file_lower:
            metadata.shot_type = ShotType.B_ROLL
        elif 'dialogue' in file_lower or 'interview' in file_lower:
            metadata.category = MediaCategory.DIALOGUE
        elif 'action' in file_lower or 'stunt' in file_lower:
            metadata.category = MediaCategory.ACTION
        elif 'ambient' in file_lower or 'background' in file_lower:
            metadata.category = MediaCategory.AMBIENT
        elif 'music' in file_lower or 'score' in file_lower:
            metadata.category = MediaCategory.MUSIC
        elif 'sfx' in file_lower or 'sound' in file_lower:
            metadata.category = MediaCategory.SFX
        
        # Generate default description if none exists
        if not metadata.description:
            metadata.description = f"Media file: {file_name}"
        
        return metadata
    
    def resolve_file(self, file_name: str, category: Optional[str] = None, 
                    shot_type: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """
        Mark a file as resolved with specified category and shot type.
        
        Returns True if resolution was successful.
        """
        if file_name not in self.files:
            return False
        
        metadata = self.files[file_name]
        
        if category:
            try:
                metadata.category = MediaCategory(category)
            except ValueError:
                return False
        
        if shot_type:
            try:
                metadata.shot_type = ShotType(shot_type)
            except ValueError:
                return False
        
        metadata.mark_resolved(notes)
        
        # Update folder state
        folder_path = str(Path(metadata.file_path).parent)
        if folder_path in self.folders:
            self.folders[folder_path].resolved_files += 1
        
        return True
    
    def reject_file(self, file_name: str, reason: str) -> bool:
        """
        Mark a file as rejected with a reason.
        
        Returns True if rejection was successful.
        """
        if file_name not in self.files:
            return False
        
        metadata = self.files[file_name]
        metadata.mark_resolved(notes=f"Rejected: {reason}")
        
        # Update folder state with issue
        folder_path = str(Path(metadata.file_path).parent)
        if folder_path in self.folders:
            self.folders[folder_path].add_issue(f"File rejected: {file_name} - {reason}")
        
        return True
    
    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file from the system.
        
        Returns True if deletion was successful.
        """
        if file_name not in self.files:
            return False
        
        metadata = self.files[file_name]
        file_path = Path(metadata.file_path)
        
        try:
            if file_path.exists():
                file_path.unlink()
                del self.files[file_name]
                return True
        except OSError:
            return False
        
        return False
    
    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files created during processing.
        
        Returns the number of files deleted.
        """
        deleted_count = 0
        temp_files = self.temp_folder.glob('*')
        
        for temp_file in temp_files:
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                    deleted_count += 1
            except OSError:
                pass
        
        return deleted_count
    
    def get_folder_status(self, folder_path: str) -> Optional[FolderState]:
        """Get the status of a folder."""
        return self.folders.get(folder_path)
    
    def get_all_folder_states(self) -> List[FolderState]:
        """Get all folder states."""
        return list(self.folders.values())
    
    def update_folder_status(self) -> None:
        """Update status of all folders based on their resolution."""
        for folder_path, folder_state in self.folders.items():
            if folder_state.is_already_done():
                folder_state.status = "complete"
            elif folder_state.total_files > 0:
                folder_state.status = "in_progress"
            else:
                folder_state.status = "pending"
            
            folder_state.last_analyzed = datetime.now(timezone.utc).isoformat()
    
    def generate_report(self) -> CleanupReport:
        """Generate a cleanup report."""
        self.update_folder_status()
        
        resolved_count = sum(1 for f in self.files.values() if f.resolved)
        rejected_count = sum(1 for f in self.files.values() if f.notes and "Rejected" in f.notes)
        total_size_freed = sum(
            f.file_size_bytes for f in self.files.values() 
            if f.notes and "Deleted" in str(f.notes)
        )
        
        issues_count = sum(len(f.issues) for f in self.folders.values())
        
        return CleanupReport(
            files_analyzed=len(self.files),
            files_resolved=resolved_count,
            files_rejected=rejected_count,
            folders_processed=len(self.folders),
            total_size_freed_bytes=total_size_freed,
            issues_found=issues_count,
            folder_states=list(self.folders.values()),
            file_metadata=list(self.files.values())
        )
    
    def close(self) -> None:
        """Clean up and close the processor."""
        self.cleanup_temp_files()
        if self.temp_folder.exists():
            try:
                self.temp_folder.rmdir()
            except OSError:
                pass


class MediaTaggingSimulator:
    """
    Simulates media tagging operations for release preparation.
    
    This class simulates the process of applying tags to media files
    as part of the release workflow.
    """
    
    def __init__(self, processor: MediaCleanupProcessor):
        self.processor = processor
        self.tag_operations: List[Dict[str, Any]] = []
    
    def add_release_tags(self, file_name: str, release_version: str) -> bool:
        """
        Add release tags to a file.
        
        Returns True if tagging was successful.
        """
        if file_name not in self.processor.files:
            return False
        
        metadata = self.processor.files[file_name]
        release_tag = f"release-{release_version}"
        build_tag = f"build-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        
        if release_tag not in metadata.tags:
            metadata.add_tag(release_tag)
        if build_tag not in metadata.tags:
            metadata.add_tag(build_tag)
        
        self.tag_operations.append({
            "operation": "add_release_tags",
            "file": file_name,
            "tags": [release_tag, build_tag],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return True
    
    def categorize_media(self, file_name: str, category: str, shot_type: str) -> bool:
        """
        Categorize a media file.
        
        Returns True if categorization was successful.
        """
        if file_name not in self.processor.files:
            return False
        
        metadata = self.processor.files[file_name]
        
        try:
            metadata.category = MediaCategory(category)
            metadata.shot_type = ShotType(shot_type)
            metadata.mark_resolved(notes=f"Categorized as {category}, {shot_type}")
            
            self.tag_operations.append({
                "operation": "categorize",
                "file": file_name,
                "category": category,
                "shot_type": shot_type,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return True
        except ValueError:
            return False
    
    def get_tag_summary(self) -> Dict[str, Any]:
        """Get a summary of all tagging operations."""
        return {
            "total_operations": len(self.tag_operations),
            "operations": self.tag_operations,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


class CombinedReleaseSimulator:
    """
    Simulates the creation of a combined release package.
    
    This class simulates the final step of gathering all processed
    media files and creating a release package.
    """
    
    def __init__(self, processor: MediaCleanupProcessor):
        self.processor = processor
        self.package_path: Optional[str] = None
        self.package_metadata: Dict[str, Any] = {}
    
    def create_release_package(self, release_version: str) -> Optional[str]:
        """
        Create a combined release package.
        
        Returns the package path if successful, None otherwise.
        """
        report = self.processor.generate_report()
        
        if not report.success:
            return None
        
        # Simulate package creation
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        package_name = f"release-{release_version}-{timestamp}"
        package_dir = self.processor.temp_folder / package_name
        
        try:
            package_dir.mkdir(parents=True, exist_ok=True)
            
            # Create metadata file
            metadata_path = package_dir / "metadata.json"
            metadata = {
                "release_version": release_version,
                "package_name": package_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "files_processed": report.files_analyzed,
                    "files_resolved": report.files_resolved,
                    "folders_processed": report.folders_processed
                }
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.package_path = str(package_dir)
            self.package_metadata = metadata
            
            return str(package_dir)
        except OSError:
            return None
    
    def get_package_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the created package."""
        if not self.package_path:
            return None
        
        return {
            "package_path": self.package_path,
            "metadata": self.package_metadata,
            "exists": os.path.exists(self.package_path) if self.package_path else False
        }
    
    def reset(self) -> None:
        """Reset the simulator state."""
        self.package_path = None
        self.package_metadata = {}
        self.processor.close()
        self.processor = MediaCleanupProcessor(self.processor.base_path)


def simulate_full_workflow(base_path: str, release_version: str) -> Dict[str, Any]:
    """
    Simulate a complete media cleanup workflow.
    
    This function orchestrates the entire workflow from scanning to
    release package creation.
    
    Args:
        base_path: The base directory for media files
        release_version: The version string for the release
        
    Returns:
        Dictionary containing the workflow results
    """
    processor = MediaCleanupProcessor(base_path)
    tagging_simulator = MediaTaggingSimulator(processor)
    release_simulator = CombinedReleaseSimulator(processor)
    
    results = {
        "workflow_id": str(uuid.uuid4()),
        "start_time": datetime.now(timezone.utc).isoformat(),
        "steps": []
    }
    
    try:
        # Step 1: Scan directory
        file_count = processor.scan_directory()
        results["steps"].append({
            "step": "scan",
            "files_found": file_count,
            "status": "success"
        })
        
        # Step 2: Analyze files
        analyzed_count = 0
        for file_name in list(processor.files.keys()):
            if processor.analyze_file(file_name):
                analyzed_count += 1
        
        results["steps"].append({
            "step": "analyze",
            "files_analyzed": analyzed_count,
            "status": "success"
        })
        
        # Step 3: Tag for release
        tagged_count = 0
        for file_name in processor.files:
            if tagging_simulator.add_release_tags(file_name, release_version):
                tagged_count += 1
        
        results["steps"].append({
            "step": "tag",
            "files_tagged": tagged_count,
            "status": "success"
        })
        
        # Step 4: Create release package
        package_path = release_simulator.create_release_package(release_version)
        results["steps"].append({
            "step": "package",
            "package_path": package_path,
            "status": "success" if package_path else "failed"
        })
        
        # Step 5: Generate final report
        report = processor.generate_report()
        results["steps"].append({
            "step": "report",
            "files_resolved": report.files_resolved,
            "issues_found": report.issues_found,
            "status": "success"
        })
        
        results["end_time"] = datetime.now(timezone.utc).isoformat()
        results["success"] = True
        
    except Exception as e:
        results["error"] = str(e)
        results["success"] = False
        results["end_time"] = datetime.now(timezone.utc).isoformat()
    
    processor.close()
    
    return results
