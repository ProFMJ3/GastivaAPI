from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Sum, Count, Avg, Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404

from apps.partners.models import Partner
from apps.offers.models import FoodOffer
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review
from .serializers import (
    PartnerStatsOverviewSerializer, PartnerRevenueChartSerializer,
    PartnerTopOffersSerializer, PartnerRecentActivitySerializer,
    PartnerOfferStatsSerializer, PartnerDashboardSerializer
)


class PartnerDashboardBaseView(APIView):
    """
    Classe de base pour les vues du dashboard partenaire.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_partner(self, partner_id=None):
        """
        Récupère le(s) partenaire(s) de l'utilisateur connecté.
        """
        user = self.request.user
        
        if user.role != 'PARTNER':
            return None
        
        if partner_id:
            # Vérifier que le partenaire appartient bien à l'utilisateur
            return get_object_or_404(Partner, id=partner_id, owner=user)
        else:
            # Retourner tous les partenaires de l'utilisateur
            return Partner.objects.filter(owner=user)


@extend_schema(
    tags=['partner-dashboard'],
    summary="Aperçu du dashboard",
    description="Retourne un aperçu global des statistiques pour le(s) partenaire(s) de l'utilisateur.",
    parameters=[
        OpenApiParameter(name='partner_id', description='ID du partenaire (optionnel)', required=False, type=int),
        OpenApiParameter(name='days', description='Nombre de jours pour les stats (défaut: 30)', required=False, type=int),
    ]
)
class PartnerDashboardOverviewView(PartnerDashboardBaseView):
    """
    Vue principale du dashboard partenaire.
    """
    
    def get(self, request):
        partner_id = request.query_params.get('partner_id')
        days = int(request.query_params.get('days', 30))
        
        partners = self.get_partner(partner_id)
        if partners is None:
            return Response(
                {"detail": "Vous n'avez pas les permissions nécessaires."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Si un seul partenaire est demandé
        if partner_id:
            partner = partners
            data = self.get_partner_stats(partner, days)
            return Response(data)
        
        # Sinon, agréger les stats de tous les partenaires
        else:
            aggregated_stats = self.get_aggregated_stats(partners, days)
            return Response(aggregated_stats)
    
    def get_partner_stats(self, partner, days):
        """
        Calcule les statistiques pour un partenaire spécifique.
        """
        now = timezone.now()
        since = now - timedelta(days=days)
        
        # ====================================================================
        # 1. STATISTIQUES DES OFFRES
        # ====================================================================
        offers = FoodOffer.objects.filter(partner=partner)
        
        total_offers = offers.count()
        active_offers = offers.filter(status=FoodOffer.Status.ACTIVE).count()
        reserved_offers = offers.filter(status=FoodOffer.Status.RESERVED).count()
        expired_offers = offers.filter(status=FoodOffer.Status.EXPIRED).count()
        sold_out_offers = offers.filter(status=FoodOffer.Status.SOLD_OUT).count()
        
        # ====================================================================
        # 2. STATISTIQUES DES COMMANDES
        # ====================================================================
        orders = Order.objects.filter(partner=partner)
        
        total_orders = orders.count()
        pending_orders = orders.filter(status=Order.Status.PENDING).count()
        confirmed_orders = orders.filter(status=Order.Status.CONFIRMED).count()
        ready_orders = orders.filter(status=Order.Status.READY).count()
        completed_orders = orders.filter(status=Order.Status.PICKED_UP).count()
        cancelled_orders = orders.filter(status=Order.Status.CANCELLED).count()
        
        # Commandes complétées (pour les revenus)
        completed = orders.filter(status=Order.Status.PICKED_UP)
        
        # Revenus
        total_revenue = completed.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Revenus aujourd'hui
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = completed.filter(
            picked_up_at__gte=today_start
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Revenus cette semaine
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_revenue = completed.filter(
            picked_up_at__gte=week_start
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Revenus ce mois
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_revenue = completed.filter(
            picked_up_at__gte=month_start
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Valeur moyenne des commandes
        avg_order = total_revenue / completed_orders if completed_orders > 0 else 0
        
        # ====================================================================
        # 3. STATISTIQUES DES AVIS
        # ====================================================================
        reviews = Review.objects.filter(order__partner=partner, is_visible=True)
        
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Distribution des notes
        rating_dist = {}
        for i in range(1, 6):
            rating_dist[str(i)] = reviews.filter(rating=i).count()
        
        # ====================================================================
        # 4. IMPACT ENVIRONNEMENTAL
        # ====================================================================
        # Estimation: 1 repas = 500g, 1kg de nourriture = 2.5kg CO2
        total_meals_saved = completed_orders  # Approximation
        total_food_saved_kg = total_meals_saved * 0.5
        total_co2_saved_kg = total_food_saved_kg * 2.5
        
        # ====================================================================
        # 5. CONSTRUCTION DE LA RÉPONSE
        # ====================================================================
        overview = {
            'total_offers': total_offers,
            'active_offers': active_offers,
            'reserved_offers': reserved_offers,
            'expired_offers': expired_offers,
            'sold_out_offers': sold_out_offers,
            
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'confirmed_orders': confirmed_orders,
            'ready_orders': ready_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'average_order_value': round(avg_order, 2),
            
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 1),
            'rating_distribution': rating_dist,
            
            'total_food_saved_kg': round(total_food_saved_kg, 2),
            'total_meals_saved': total_meals_saved,
            'total_co2_saved_kg': round(total_co2_saved_kg, 2),
        }
        
        # Données pour les graphiques
        revenue_chart = self.get_revenue_chart_data(partner, days)
        top_offers = self.get_top_offers(partner)
        recent_activity = self.get_recent_activity(partner)
        offers_stats = self.get_offers_stats(partner)
        
        partner_info = {
            'id': partner.id,
            'name': partner.name,
            'quarter': partner.quarter,
            'logo': partner.logo.url if partner.logo else None,
            'status': partner.status,
            'is_open_now': partner.is_open_now(),
        }
        
        return {
            'partner_info': partner_info,
            'overview': overview,
            'revenue_chart': revenue_chart,
            'top_offers': top_offers,
            'recent_activity': recent_activity,
            'offers_stats': offers_stats,
        }
    
    def get_aggregated_stats(self, partners, days):
        """
        Agrège les statistiques pour plusieurs partenaires.
        """
        # Cette méthode est optionnelle - à implémenter si nécessaire
        partner_list = []
        total_stats = {}
        
        for partner in partners:
            stats = self.get_partner_stats(partner, days)
            partner_list.append({
                'id': partner.id,
                'name': partner.name,
                'stats': stats['overview']
            })
        
        return {
            'partners': partner_list,
            'total_partners': partners.count(),
        }
    
    def get_revenue_chart_data(self, partner, days):
        """
        Génère les données pour le graphique des revenus.
        """
        now = timezone.now()
        since = now - timedelta(days=days)
        
        # Commandes complétées par jour
        daily_revenue = Order.objects.filter(
            partner=partner,
            status=Order.Status.PICKED_UP,
            picked_up_at__gte=since
        ).annotate(
            date=TruncDate('picked_up_at')
        ).values('date').annotate(
            revenue=Sum('total_amount'),
            orders=Count('id')
        ).order_by('date')
        
        labels = []
        revenue_data = []
        orders_data = []
        
        # Créer un dictionnaire pour un accès facile
        revenue_dict = {item['date']: item for item in daily_revenue}
        
        # Remplir tous les jours de la période
        for i in range(days):
            date = (since + timedelta(days=i)).date()
            labels.append(date.strftime('%d/%m'))
            
            if date in revenue_dict:
                revenue_data.append(float(revenue_dict[date]['revenue']))
                orders_data.append(revenue_dict[date]['orders'])
            else:
                revenue_data.append(0)
                orders_data.append(0)
        
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Revenus (FCFA)',
                    'data': revenue_data,
                    'borderColor': '#4CAF50',
                    'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                },
                {
                    'label': 'Commandes',
                    'data': orders_data,
                    'borderColor': '#2196F3',
                    'backgroundColor': 'rgba(33, 150, 243, 0.1)',
                }
            ]
        }
    
    def get_top_offers(self, partner):
        """
        Récupère les offres les plus vendues.
        """
        top_offers = OrderItem.objects.filter(
            order__partner=partner,
            order__status=Order.Status.PICKED_UP
        ).values(
            'offer_id', 'offer__title'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price')),
            orders_count=Count('order', distinct=True)
        ).order_by('-total_quantity')[:5]
        
        return [
            {
                'offer_id': item['offer_id'],
                'offer_title': item['offer__title'],
                'total_quantity': item['total_quantity'],
                'total_revenue': float(item['total_revenue']),
                'orders_count': item['orders_count'],
            }
            for item in top_offers
        ]
    
    def get_recent_activity(self, partner):
        """
        Récupère les activités récentes.
        """
        activities = []
        
        # Dernières commandes
        recent_orders = Order.objects.filter(
            partner=partner
        ).order_by('-created_at')[:5]
        
        for order in recent_orders:
            activities.append({
                'id': order.id,
                'type': 'order',
                'title': f"Commande {order.order_number}",
                'description': f"{order.client.get_full_name()} - {order.total_amount} FCFA",
                'time_ago': self.get_time_ago(order.created_at),
                'status': order.status,
                'link': f'/orders/{order.id}',
            })
        
        # Dernières offres créées
        recent_offers = FoodOffer.objects.filter(
            partner=partner
        ).order_by('-created_at')[:5]
        
        for offer in recent_offers:
            activities.append({
                'id': offer.id,
                'type': 'offer',
                'title': f"Nouvelle offre: {offer.title}",
                'description': f"{offer.discounted_price} FCFA ({offer.remaining_quantity}/{offer.quantity_available} dispo)",
                'time_ago': self.get_time_ago(offer.created_at),
                'status': offer.status,
                'link': f'/offers/{offer.id}',
            })
        
        # Derniers avis
        recent_reviews = Review.objects.filter(
            order__partner=partner
        ).order_by('-created_at')[:5]
        
        for review in recent_reviews:
            activities.append({
                'id': review.id,
                'type': 'review',
                'title': f"Nouvel avis {review.rating}★",
                'description': review.comment[:50] + ('...' if review.comment and len(review.comment) > 50 else ''),
                'time_ago': self.get_time_ago(review.created_at),
                'status': None,
                'link': f'/reviews/{review.id}',
            })
        
        # Trier par date (le plus récent d'abord) et limiter à 10
        activities.sort(key=lambda x: x.get('_created_at', timezone.now()), reverse=True)
        
        return activities[:10]
    
    def get_offers_stats(self, partner):
        """
        Statistiques détaillées pour chaque offre.
        """
        offers = FoodOffer.objects.filter(partner=partner)
        stats = []
        
        for offer in offers:
            # Commandes pour cette offre
            order_items = OrderItem.objects.filter(
                offer=offer,
                order__status=Order.Status.PICKED_UP
            )
            
            total_quantity_sold = order_items.aggregate(total=Sum('quantity'))['total'] or 0
            total_revenue = order_items.aggregate(
                total=Sum(F('quantity') * F('unit_price'))
            )['total'] or 0
            total_orders = order_items.values('order').distinct().count()
            
            # Taux de conversion
            conversion_rate = (total_quantity_sold / offer.quantity_available * 100) if offer.quantity_available > 0 else 0
            
            # Performance
            if conversion_rate >= 70:
                performance = 'good'
            elif conversion_rate >= 30:
                performance = 'average'
            else:
                performance = 'poor'
            
            # Temps restant
            if offer.pickup_deadline > timezone.now():
                delta = offer.pickup_deadline - timezone.now()
                if delta.days > 0:
                    time_remaining = f"{delta.days}j {delta.seconds//3600}h"
                elif delta.seconds//3600 > 0:
                    time_remaining = f"{delta.seconds//3600}h {(delta.seconds//60)%60}min"
                else:
                    time_remaining = f"{delta.seconds//60}min"
            else:
                time_remaining = "Expirée"
            
            stats.append({
                'id': offer.id,
                'title': offer.title,
                'discounted_price': offer.discounted_price,
                'original_price': offer.original_price,
                'quantity_available': offer.quantity_available,
                'quantity_reserved': offer.quantity_reserved,
                'quantity_sold': offer.quantity_sold,
                'status': offer.status,
                'pickup_deadline': offer.pickup_deadline,
                'created_at': offer.created_at,
                'total_orders': total_orders,
                'total_quantity_sold': total_quantity_sold,
                'total_revenue': total_revenue,
                'conversion_rate': round(conversion_rate, 1),
                'time_remaining': time_remaining,
                'performance': performance,
            })
        
        return stats
    
    def get_time_ago(self, dt):
        """
        Convertit une datetime en texte relatif.
        """
        delta = timezone.now() - dt
        if delta.days > 30:
            months = delta.days // 30
            return f"il y a {months} mois"
        elif delta.days > 0:
            return f"il y a {delta.days} jours"
        elif delta.seconds // 3600 > 0:
            return f"il y a {delta.seconds // 3600} heures"
        elif delta.seconds // 60 > 0:
            return f"il y a {delta.seconds // 60} minutes"
        else:
            return "à l'instant"


@extend_schema(
    tags=['partner-dashboard'],
    summary="Statistiques des offres",
    description="Retourne les statistiques détaillées pour chaque offre du partenaire.",
)
class PartnerOffersStatsView(PartnerDashboardBaseView):
    """
    Statistiques détaillées des offres.
    """
    
    def get(self, request):
        partner_id = request.query_params.get('partner_id')
        partners = self.get_partner(partner_id)
        
        if partners is None:
            return Response(
                {"detail": "Vous n'avez pas les permissions nécessaires."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if partner_id:
            partner = partners
            offers_stats = self.get_offers_stats(partner)
            return Response(offers_stats)
        else:
            # Agrégation pour plusieurs partenaires
            all_stats = []
            for partner in partners:
                stats = self.get_offers_stats(partner)
                all_stats.extend(stats)
            return Response(all_stats)
    
    def get_offers_stats(self, partner):
        """
        Identique à la méthode dans la vue précédente.
        """
        # Même implémentation que ci-dessus
        pass


@extend_schema(
    tags=['partner-dashboard'],
    summary="Revenus par période",
    description="Retourne les revenus pour une période spécifique.",
    parameters=[
        OpenApiParameter(name='partner_id', description='ID du partenaire', required=False, type=int),
        OpenApiParameter(name='period', description='Période: day, week, month, year', required=True, type=str),
    ]
)
class PartnerRevenueView(PartnerDashboardBaseView):
    """
    Revenus par période.
    """
    
    def get(self, request):
        partner_id = request.query_params.get('partner_id')
        period = request.query_params.get('period', 'month')
        
        partners = self.get_partner(partner_id)
        if partners is None:
            return Response(
                {"detail": "Vous n'avez pas les permissions nécessaires."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if partner_id:
            partner = partners
            data = self.get_revenue_by_period(partner, period)
            return Response(data)
        else:
            # Agrégation
            all_data = []
            for partner in partners:
                data = self.get_revenue_by_period(partner, period)
                all_data.append({
                    'partner_id': partner.id,
                    'partner_name': partner.name,
                    'data': data
                })
            return Response(all_data)
    
    def get_revenue_by_period(self, partner, period):
        """
        Agrège les revenus par période.
        """
        now = timezone.now()
        
        if period == 'day':
            # Revenus par heure aujourd'hui
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            orders = Order.objects.filter(
                partner=partner,
                status=Order.Status.PICKED_UP,
                picked_up_at__gte=today_start
            )
            # ... implémentation
            pass
        
        elif period == 'week':
            # Revenus par jour cette semaine
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            # ... implémentation
            pass
        
        elif period == 'month':
            # Revenus par jour ce mois
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # ... implémentation
            pass
        
        elif period == 'year':
            # Revenus par mois cette année
            year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            # ... implémentation
            pass
        
        return {}