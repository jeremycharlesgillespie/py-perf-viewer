import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseNotFound, HttpResponseServerError
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
from .services import dynamodb_service
from .models import PerformanceRecord, PerformanceMetrics
from .system_services import system_data_service
from .system_models import SystemDataRecord, SystemSummary
from typing import Optional

logger = logging.getLogger(__name__)


def dashboard_home(request):
    """Main dashboard view."""
    # Get recent performance metrics
    metrics = dynamodb_service.get_performance_metrics()
    recent_records = dynamodb_service.get_recent_records(hours=24, limit=20)
    
    # Get system performance data
    system_dashboard_data = system_data_service.get_system_dashboard_data()
    
    # Get filter options
    hostnames = dynamodb_service.get_unique_hostnames()
    function_names = dynamodb_service.get_unique_function_names()
    system_hostnames = system_data_service.get_system_hostnames()
    
    context = {
        'metrics': metrics,
        'recent_records': recent_records,
        'hostnames': hostnames,
        'function_names': function_names,
        'system_data': system_dashboard_data,
        'system_hostnames': system_hostnames,
    }
    
    return render(request, 'dashboard/home.html', context)


def performance_records(request):
    """View for browsing performance records with filtering."""
    # Get filter parameters
    hostname = request.GET.get('hostname')
    function_name = request.GET.get('function_name')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    session_id = request.GET.get('session_id')
    sort_by = request.GET.get('sort_by', 'timestamp')
    order = request.GET.get('order', 'desc')
    
    # Parse dates
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            pass
    
    # If no date range specified, default to last 7 days
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
    
    # Fetch filtered records
    records = dynamodb_service.get_filtered_records(
        hostname=hostname,
        start_date=start_date,
        end_date=end_date,
        function_name=function_name,
        session_id=session_id,
        limit=200
    )
    
    # Sort records
    reverse_sort = order == 'desc'
    if sort_by == 'timestamp':
        records.sort(key=lambda r: r.timestamp, reverse=reverse_sort)
    elif sort_by == 'hostname':
        records.sort(key=lambda r: r.hostname, reverse=reverse_sort)
    elif sort_by == 'total_calls':
        records.sort(key=lambda r: r.total_calls, reverse=reverse_sort)
    elif sort_by == 'total_wall_time':
        records.sort(key=lambda r: r.total_wall_time, reverse=reverse_sort)
    elif sort_by == 'avg_wall_time':
        records.sort(key=lambda r: r.avg_wall_time_per_call, reverse=reverse_sort)
    
    # Paginate results
    paginator = Paginator(records, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    hostnames = dynamodb_service.get_unique_hostnames()
    function_names = dynamodb_service.get_unique_function_names()
    
    context = {
        'records': page_obj,
        'hostnames': hostnames,
        'function_names': function_names,
        'current_filters': {
            'hostname': hostname,
            'function_name': function_name,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'session_id': session_id,
            'sort_by': sort_by,
            'order': order,
        },
        'total_records': len(records),
    }
    
    return render(request, 'dashboard/records.html', context)


def record_detail(request, record_id):
    """Detailed view of a single performance record."""
    try:
        # Get all records and find the one with matching ID
        records = dynamodb_service.get_all_records(limit=1000)
        record = None
        for r in records:
            if r.id == record_id:
                record = r
                break
        
        if not record:
            return HttpResponseNotFound(render(request, 'dashboard/record_not_found.html', {'record_id': record_id}).content)
        
        # Get related records from the same session
        session_records = dynamodb_service.get_records_by_session(record.session_id)
        session_records.sort(key=lambda r: r.timestamp)
        
        context = {
            'record': record,
            'session_records': session_records,
            'function_count': len(record.function_names),
            'slowest_functions': record.get_slowest_functions(),
            'most_called_functions': record.get_most_called_functions(),
        }
        
        return render(request, 'dashboard/record_detail.html', context)
    
    except Exception as e:
        return HttpResponseServerError(render(request, 'dashboard/error.html', {'error': str(e)}).content)


def function_analysis(request, function_name):
    """Analysis view for a specific function across all records."""
    try:
        records = dynamodb_service.get_records_with_function(function_name, limit=200)
        
        if not records:
            return HttpResponseNotFound(render(request, 'dashboard/function_not_found.html', {'function_name': function_name}).content)
        
        # Analyze function performance across records
        function_stats = []
        total_calls = 0
        total_wall_time = 0
        total_cpu_time = 0
        
        for record in records:
            stats = record.get_function_stats(function_name)
            if stats:
                function_stats.append({
                    'record': record,
                    'stats': stats,
                    'calls': stats.get('call_count', 0),
                    'avg_wall_time': stats.get('wall_time', {}).get('average', 0),
                    'total_wall_time': stats.get('wall_time', {}).get('total', 0),
                    'avg_cpu_time': stats.get('cpu_time', {}).get('average', 0),
                })
                total_calls += stats.get('call_count', 0)
                total_wall_time += stats.get('wall_time', {}).get('total', 0)
                total_cpu_time += stats.get('cpu_time', {}).get('total', 0)
        
        # Sort by average wall time (slowest first)
        function_stats.sort(key=lambda x: x['avg_wall_time'], reverse=True)
        
        # Calculate aggregate statistics
        avg_wall_time = total_wall_time / total_calls if total_calls > 0 else 0
        avg_cpu_time = total_cpu_time / total_calls if total_calls > 0 else 0
        
        context = {
            'function_name': function_name,
            'function_stats': function_stats,
            'total_records': len(records),
            'total_calls': total_calls,
            'total_wall_time': total_wall_time,
            'total_cpu_time': total_cpu_time,
            'avg_wall_time': avg_wall_time,
            'avg_cpu_time': avg_cpu_time,
        }
        
        return render(request, 'dashboard/function_analysis.html', context)
    
    except Exception as e:
        return HttpResponseServerError(render(request, 'dashboard/error.html', {'error': str(e)}).content)


def api_metrics(request):
    """API endpoint for performance metrics."""
    hostname = request.GET.get('hostname')
    function_name = request.GET.get('function_name')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            pass
    
    metrics = dynamodb_service.get_performance_metrics(
        hostname=hostname,
        start_date=start_date,
        end_date=end_date,
        function_name=function_name
    )
    
    return JsonResponse({
        'total_records': metrics.total_records,
        'total_sessions': metrics.total_sessions,
        'unique_hostnames': metrics.unique_hostnames,
        'unique_functions': metrics.unique_functions,
        'avg_session_duration': metrics.avg_session_duration,
        'slowest_functions': metrics.slowest_functions_global,
        'most_active_hosts': metrics.most_active_hosts,
    })


def api_hostnames(request):
    """API endpoint for unique hostnames."""
    hostnames = dynamodb_service.get_unique_hostnames()
    return JsonResponse({'hostnames': hostnames})


def api_functions(request):
    """API endpoint for unique function names."""
    functions = dynamodb_service.get_unique_function_names()
    return JsonResponse({'functions': functions})


def timeline_viewer(request):
    """Timeline viewer for system and process monitoring data."""
    session_id = request.GET.get('session_id')
    hostname = request.GET.get('hostname')
    
    if not session_id:
        # Get recent sessions with system monitoring data
        recent_sessions = dynamodb_service.get_sessions_with_system_data(limit=10)
        return render(request, 'dashboard/timeline_select.html', {'sessions': recent_sessions})
    
    # Get timeline data for the specific session
    timeline_data = dynamodb_service.get_timeline_data(session_id)
    
    if not timeline_data:
        return HttpResponseNotFound(render(request, 'dashboard/timeline_not_found.html', {'session_id': session_id}).content)
    
    context = {
        'session_id': session_id,
        'hostname': hostname,
        'timeline_data': timeline_data,
        'has_system_data': bool(timeline_data.get('system')),
        'has_process_data': bool(timeline_data.get('processes')),
        'metadata': timeline_data.get('metadata', {}),
    }
    
    return render(request, 'dashboard/timeline_viewer.html', context)


def api_timeline_data(request):
    """API endpoint for timeline data."""
    session_id = request.GET.get('session_id')
    data_type = request.GET.get('type', 'all')  # 'system', 'process', or 'all'
    
    if not session_id:
        return JsonResponse({'error': 'session_id is required'}, status=400)
    
    timeline_data = dynamodb_service.get_timeline_data(session_id)
    
    if not timeline_data:
        return JsonResponse({'error': 'Timeline data not found'}, status=404)
    
    response_data = {'metadata': timeline_data.get('metadata', {})}
    
    if data_type in ['system', 'all']:
        response_data['system'] = timeline_data.get('system', [])
    
    if data_type in ['process', 'all']:
        response_data['processes'] = timeline_data.get('processes', {})
    
    return JsonResponse(response_data)


def system_metrics(request):
    """System metrics dashboard view."""
    hostname = request.GET.get('hostname')
    hours = int(request.GET.get('hours', 24))
    
    if hostname:
        # Show detailed metrics for specific hostname
        system_metrics_data = system_data_service.get_system_metrics_for_hostname(hostname, hours)
        context = {
            'hostname': hostname,
            'system_metrics': system_metrics_data,
            'timeline_data': system_metrics_data.get('timeline_data', []),
            'hours': hours,
        }
        return render(request, 'dashboard/system_detail.html', context)
    else:
        # Show overview of all system hosts
        dashboard_data = system_data_service.get_system_dashboard_data()
        context = {
            'system_data': dashboard_data,
            'hours': hours,
        }
        return render(request, 'dashboard/system_overview.html', context)


def api_system_metrics(request):
    """API endpoint for system metrics data."""
    hostname = request.GET.get('hostname')
    hours = int(request.GET.get('hours', 24))
    
    # Try optimized service first, fall back to legacy service
    try:
        from .optimized_system_service import optimized_system_service
        
        # Test if optimized table exists
        if optimized_system_service.test_connection():
            if hostname:
                metrics_data = optimized_system_service.get_system_metrics_for_hostname(hostname, hours)
                return JsonResponse(metrics_data)
            else:
                dashboard_data = optimized_system_service.get_system_dashboard_data()
                return JsonResponse(dashboard_data)
    except Exception as e:
        logger.warning(f"Optimized service failed, falling back to legacy: {e}")
    
    # Fallback to legacy service
    if hostname:
        metrics_data = system_data_service.get_system_metrics_for_hostname(hostname, hours)
        return JsonResponse(metrics_data)
    else:
        dashboard_data = system_data_service.get_system_dashboard_data()
        return JsonResponse(dashboard_data)


def api_system_hostnames(request):
    """API endpoint for system hostnames."""
    hostnames = system_data_service.get_system_hostnames()
    return JsonResponse({'hostnames': hostnames})


def spa_view(request):
    """Serve the Vue.js Single Page Application."""
    return render(request, 'spa/index.html')
