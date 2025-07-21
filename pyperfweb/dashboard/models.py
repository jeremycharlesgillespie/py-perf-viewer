from django.db import models
from django.utils import timezone
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import json


@dataclass
class PerformanceRecord:
    """Dataclass representing a PyPerf performance record from DynamoDB."""
    id: str
    session_id: str
    timestamp: float
    hostname: str
    total_calls: int
    total_wall_time: float
    total_cpu_time: float
    data: Dict[str, Any]
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'PerformanceRecord':
        """Create PerformanceRecord from DynamoDB item."""
        return cls(
            id=item['id']['N'],
            session_id=item['session_id']['S'],
            timestamp=float(item['timestamp']['N']),
            hostname=item['hostname']['S'],
            total_calls=int(item['total_calls']['N']),
            total_wall_time=float(item['total_wall_time']['N']),
            total_cpu_time=float(item['total_cpu_time']['N']),
            data=json.loads(item['data']['S'])
        )
    
    @property
    def datetime(self):
        """Convert timestamp to datetime object."""
        from datetime import datetime, timezone as dt_timezone
        return datetime.fromtimestamp(self.timestamp, tz=dt_timezone.utc)
    
    @property
    def function_summaries(self) -> Dict[str, Any]:
        """Get function summaries from data."""
        return self.data.get('function_summaries', {})
    
    @property
    def detailed_results(self) -> Dict[str, Any]:
        """Get detailed results from data."""
        return self.data.get('detailed_results', {})
    
    @property
    def function_names(self) -> List[str]:
        """Get list of function names in this record."""
        return list(self.function_summaries.keys())
    
    @property
    def avg_wall_time_per_call(self) -> float:
        """Calculate average wall time per call."""
        if self.total_calls > 0:
            return self.total_wall_time / self.total_calls
        return 0.0
    
    @property
    def avg_cpu_time_per_call(self) -> float:
        """Calculate average CPU time per call."""
        if self.total_calls > 0:
            return self.total_cpu_time / self.total_calls
        return 0.0
    
    def get_function_stats(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific function."""
        return self.function_summaries.get(function_name)
    
    def get_slowest_functions(self, limit: int = 5) -> List[tuple]:
        """Get the slowest functions by average wall time."""
        functions = []
        for func_name, stats in self.function_summaries.items():
            avg_time = stats.get('wall_time', {}).get('average', 0)
            functions.append((func_name, avg_time))
        
        functions.sort(key=lambda x: x[1], reverse=True)
        return functions[:limit]
    
    def get_most_called_functions(self, limit: int = 5) -> List[tuple]:
        """Get the most frequently called functions."""
        functions = []
        for func_name, stats in self.function_summaries.items():
            call_count = stats.get('call_count', 0)
            functions.append((func_name, call_count))
        
        functions.sort(key=lambda x: x[1], reverse=True)
        return functions[:limit]


@dataclass
class PerformanceMetrics:
    """Aggregate performance metrics across multiple records."""
    total_records: int
    total_sessions: int
    unique_hostnames: List[str]
    unique_functions: List[str]
    date_range: tuple
    avg_session_duration: float
    slowest_functions_global: List[tuple]
    most_active_hosts: List[tuple]
    
    @classmethod
    def from_records(cls, records: List[PerformanceRecord]) -> 'PerformanceMetrics':
        """Calculate aggregate metrics from a list of records."""
        if not records:
            return cls(0, 0, [], [], (None, None), 0.0, [], [])
        
        # Basic counts
        total_records = len(records)
        unique_sessions = len(set(r.session_id for r in records))
        unique_hostnames = list(set(r.hostname for r in records))
        
        # Function analysis
        all_functions = set()
        function_times = {}
        host_activity = {}
        
        for record in records:
            all_functions.update(record.function_names)
            
            # Track host activity
            if record.hostname not in host_activity:
                host_activity[record.hostname] = 0
            host_activity[record.hostname] += record.total_calls
            
            # Aggregate function performance
            for func_name, stats in record.function_summaries.items():
                if func_name not in function_times:
                    function_times[func_name] = []
                function_times[func_name].append(stats.get('wall_time', {}).get('average', 0))
        
        # Calculate global slowest functions
        slowest_functions = []
        for func_name, times in function_times.items():
            avg_time = sum(times) / len(times) if times else 0
            slowest_functions.append((func_name, avg_time))
        slowest_functions.sort(key=lambda x: x[1], reverse=True)
        
        # Most active hosts
        most_active_hosts = sorted(host_activity.items(), key=lambda x: x[1], reverse=True)
        
        # Date range
        timestamps = [r.timestamp for r in records]
        date_range = (min(timestamps), max(timestamps)) if timestamps else (None, None)
        
        # Average session duration (approximate)
        session_durations = {}
        for record in records:
            if record.session_id not in session_durations:
                session_durations[record.session_id] = []
            session_durations[record.session_id].append(record.timestamp)
        
        avg_duration = 0.0
        if session_durations:
            durations = []
            for timestamps in session_durations.values():
                if len(timestamps) > 1:
                    durations.append(max(timestamps) - min(timestamps))
            avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return cls(
            total_records=total_records,
            total_sessions=unique_sessions,
            unique_hostnames=unique_hostnames,
            unique_functions=list(all_functions),
            date_range=date_range,
            avg_session_duration=avg_duration,
            slowest_functions_global=slowest_functions[:10],
            most_active_hosts=most_active_hosts[:10]
        )
