"""
Предсказание нарушений SLA с использованием простого машинного обучения (на базе numpy)
"""
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from .models import SLATracking, Endpoint


class SLAForecaster:
    """Класс для прогнозирования нарушений SLA"""
    
    @staticmethod
    def _linear_regression_numpy(x, y):
        """
        Простая линейная регрессия используя numpy
        Возвращает коэффициенты [slope, intercept]
        """
        # Используем numpy.polyfit для линейной регрессии (степень 1)
        coefficients = np.polyfit(x, y, 1)
        return coefficients
    
    @staticmethod
    def predict_breach(endpoint, forecast_days=1):
        """
        Предсказать вероятность нарушения SLA в ближайшие дни
        
        Args:
            endpoint: Endpoint объект
            forecast_days: количество дней для предсказания
            
        Returns:
            dict с предсказанием и вероятностью
        """
        # Получить данные за последние 30 дней
        today = timezone.now().date()
        start_date = today - timedelta(days=30)
        
        sla_records = SLATracking.objects.filter(
            endpoint=endpoint,
            date__gte=start_date,
            date__lte=today
        ).order_by('date')
        
        if sla_records.count() < 5:
            # Недостаточно данных
            return {
                'predicted_breach': False,
                'breach_probability': 0.0,
                'confidence': 0.0,
                'reason': 'Insufficient historical data',
                'days_ahead': forecast_days,
            }
        
        # Подготовить данные для обучения
        data = []
        for i, record in enumerate(sla_records):
            data.append({
                'day': i,
                'sla': record.actual_sla,
                'breached': 1 if record.sla_breached else 0,
                'error_rate': (100 - record.actual_sla) / 100,
            })
        
        # Проверить тренд
        sla_values = [d['sla'] for d in data]
        
        # Линейная регрессия для тренда используя numpy
        X = np.array([i for i in range(len(sla_values))])
        y = np.array(sla_values)
        
        # Получить коэффициенты линейной регрессии
        # coefficients[0] = slope (наклон), coefficients[1] = intercept
        coefficients = SLAForecaster._linear_regression_numpy(X, y)
        slope = coefficients[0]
        intercept = coefficients[1]
        
        # Предсказать SLA на forecast_days дней вперед
        future_x = len(sla_values) + forecast_days - 1
        predicted_sla = float(slope * future_x + intercept)
        
        # Ограничить прогноз в диапазон
        predicted_sla = max(0, min(100, predicted_sla))
        
        # Целевой SLA
        target_sla = (1 - endpoint.sla_error_rate) * 100
        
        # Определить вероятность нарушения
        predicted_breach = predicted_sla < target_sla
        
        # Рассчитать вероятность на основе исторических данных и тренда
        historical_breach_rate = sum(1 for d in data if d['breached']) / len(data)
        
        if slope < 0:  # Тренд ухудшается
            breach_probability = min(0.99, historical_breach_rate + 0.2)
        elif slope > 0:  # Тренд улучшается
            breach_probability = max(0.01, historical_breach_rate - 0.2)
        else:
            breach_probability = historical_breach_rate
        
        # Вычислить уверенность на основе стабильности данных
        sla_std = float(np.std(sla_values))
        confidence = max(0.3, min(0.99, 1.0 - (sla_std / 100)))
        
        return {
            'predicted_breach': predicted_breach,
            'breach_probability': float(breach_probability),
            'predicted_sla': predicted_sla,
            'target_sla': target_sla,
            'confidence': float(confidence),
            'trend': 'improving' if slope > 0 else ('stable' if abs(slope) < 0.1 else 'deteriorating'),
            'days_ahead': forecast_days,
            'recent_breaches': sum(1 for d in data[-7:] if d['breached']),
        }
    
    @staticmethod
    def predict_all_endpoints(project, forecast_days=1):
        """
        Предсказать нарушения SLA для всех эндпоинтов проекта
        
        Returns:
            list предсказаний
        """
        endpoints = project.endpoint_set.all()
        predictions = []
        
        for endpoint in endpoints:
            pred = SLAForecaster.predict_breach(endpoint, forecast_days)
            predictions.append({
                'endpoint': endpoint,
                'prediction': pred,
            })
        
        return predictions
    
    @staticmethod
    def get_anomalies(endpoint, window_size=7):
        """
        Обнаружить аномальные дни в SLA
        
        Returns:
            list дат с аномалиями
        """
        today = timezone.now().date()
        start_date = today - timedelta(days=window_size * 2)
        
        sla_records = SLATracking.objects.filter(
            endpoint=endpoint,
            date__gte=start_date,
            date__lte=today
        ).order_by('date')
        
        if sla_records.count() < window_size:
            return []
        
        sla_values = np.array(list(sla_records.values_list('actual_sla', flat=True)))
        
        # Рассчитать среднее и стандартное отклонение
        mean_sla = np.mean(sla_values)
        std_sla = np.std(sla_values)
        
        # Найти значения, которые выходят за пределы 2 стандартных отклонений
        threshold = 2 * std_sla
        anomalies = []
        
        for record in sla_records:
            if abs(record.actual_sla - mean_sla) > threshold:
                anomalies.append({
                    'date': record.date,
                    'sla': record.actual_sla,
                    'deviation': abs(record.actual_sla - mean_sla),
                })
        
        return anomalies
    
    @staticmethod
    def get_forecast_summary(project, days_ahead=7):
        """
        Получить итоговый прогноз по проекту на ближайшие дни
        
        Returns:
            dict со сводкой прогнозов
        """
        predictions = SLAForecaster.predict_all_endpoints(project, days_ahead)
        
        endpoints_at_risk = [p for p in predictions if p['prediction']['predicted_breach']]
        high_risk = [p for p in endpoints_at_risk if p['prediction']['breach_probability'] > 0.7]
        
        avg_confidence = float(np.mean([p['prediction']['confidence'] for p in predictions]))
        avg_breach_probability = float(np.mean([p['prediction']['breach_probability'] for p in predictions]))
        
        return {
            'forecast_days': days_ahead,
            'total_endpoints': len(predictions),
            'endpoints_at_risk': len(endpoints_at_risk),
            'high_risk_count': len(high_risk),
            'avg_breach_probability': avg_breach_probability,
            'avg_confidence': avg_confidence,
            'predictions': predictions,
            'high_risk_endpoints': high_risk,
            'summary': f"Прогноз: {len(endpoints_at_risk)} эндпоинтов из {len(predictions)} подвергаются риску нарушения SLA в следующие {days_ahead} дней.",
        }
