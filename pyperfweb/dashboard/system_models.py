"""
Data models for system performance data.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class SystemMetric:
    """Individual system metric data point."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_used_mb: float
    load_avg_1m: Optional[float] = None
    load_avg_5m: Optional[float] = None
    load_avg_15m: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemMetric':
        """Create SystemMetric from dictionary."""
        return cls(
            timestamp=data.get('timestamp', 0),
            cpu_percent=data.get('cpu_percent', 0),
            memory_percent=data.get('memory_percent', 0),
            memory_available_mb=data.get('memory_available_mb', 0),
            memory_used_mb=data.get('memory_used_mb', 0),
            load_avg_1m=data.get('load_avg_1m'),
            load_avg_5m=data.get('load_avg_5m'),
            load_avg_15m=data.get('load_avg_15m')
        )
    
    @property
    def datetime(self):
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp)
    
    @property
    def memory_total_mb(self) -> float:
        """Calculate total memory in MB."""
        return self.memory_available_mb + self.memory_used_mb


@dataclass
class ProcessMetric:
    """Individual process metric data point."""
    timestamp: float
    pid: int
    name: str
    cpu_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    num_threads: int
    status: str
    create_time: float
    cmdline: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessMetric':
        """Create ProcessMetric from dictionary."""
        return cls(
            timestamp=data.get('timestamp', 0),
            pid=data.get('pid', 0),
            name=data.get('name', ''),
            cpu_percent=data.get('cpu_percent', 0),
            memory_rss_mb=data.get('memory_rss_mb', 0),
            memory_vms_mb=data.get('memory_vms_mb', 0),
            num_threads=data.get('num_threads', 0),
            status=data.get('status', ''),
            create_time=data.get('create_time', 0),
            cmdline=data.get('cmdline', '')
        )
    
    @property
    def datetime(self):
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp)


@dataclass
class SystemDataRecord:
    """Complete system data record from DynamoDB."""
    id: int
    hostname: str
    timestamp: float
    batch_size: int
    start_time: float
    end_time: float
    created_at: str
    system_metrics: List[SystemMetric]
    process_metrics: Dict[str, List[ProcessMetric]]
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'SystemDataRecord':
        """Create SystemDataRecord from DynamoDB item."""
        # Parse metrics data
        system_metrics = []
        process_metrics = {}
        
        if 'parsed_metrics' in item:
            for metric_data in item['parsed_metrics']:
                # Parse system metrics
                if 'system' in metric_data:
                    system_metrics.append(SystemMetric.from_dict(metric_data['system']))
                
                # Parse process metrics
                if 'processes' in metric_data:
                    for pid, process_data in metric_data['processes'].items():
                        if pid not in process_metrics:
                            process_metrics[pid] = []
                        process_metrics[pid].append(ProcessMetric.from_dict(process_data))
        
        return cls(
            id=item.get('id', 0),
            hostname=item.get('hostname', ''),
            timestamp=item.get('timestamp', 0),
            batch_size=item.get('batch_size', 0),
            start_time=item.get('start_time', 0),
            end_time=item.get('end_time', 0),
            created_at=item.get('created_at', ''),
            system_metrics=system_metrics,
            process_metrics=process_metrics
        )
    
    @property
    def datetime(self):
        """Convert timestamp to datetime object."""
        return datetime.fromtimestamp(self.timestamp)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration of this batch in seconds."""
        return self.end_time - self.start_time
    
    @property
    def avg_cpu_percent(self) -> float:
        """Calculate average CPU percentage for this batch."""
        if not self.system_metrics:
            return 0.0
        return sum(m.cpu_percent for m in self.system_metrics) / len(self.system_metrics)
    
    @property
    def avg_memory_percent(self) -> float:
        """Calculate average memory percentage for this batch."""
        if not self.system_metrics:
            return 0.0
        return sum(m.memory_percent for m in self.system_metrics) / len(self.system_metrics)
    
    @property
    def max_cpu_percent(self) -> float:
        """Get maximum CPU percentage for this batch."""
        if not self.system_metrics:
            return 0.0
        return max(m.cpu_percent for m in self.system_metrics)
    
    @property
    def max_memory_percent(self) -> float:
        """Get maximum memory percentage for this batch."""
        if not self.system_metrics:
            return 0.0
        return max(m.memory_percent for m in self.system_metrics)


@dataclass
class SystemSummary:
    """Summary statistics for system performance data."""
    hostname: str
    total_records: int
    time_range_start: Optional[float]
    time_range_end: Optional[float]
    avg_cpu_percent: float
    avg_memory_percent: float
    max_cpu_percent: float
    max_memory_percent: float
    total_processes_tracked: int
    last_seen: float
    
    @property
    def datetime_range(self) -> tuple:
        """Get datetime range tuple."""
        start = datetime.fromtimestamp(self.time_range_start) if self.time_range_start else None
        end = datetime.fromtimestamp(self.time_range_end) if self.time_range_end else None
        return (start, end)
    
    @property
    def last_seen_datetime(self):
        """Convert last seen timestamp to datetime."""
        return datetime.fromtimestamp(self.last_seen)
    
    @property
    def duration_hours(self) -> float:
        """Calculate duration in hours."""
        if self.time_range_start and self.time_range_end:
            return (self.time_range_end - self.time_range_start) / 3600
        return 0.0