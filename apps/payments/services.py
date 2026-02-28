"""
Service de simulation de paiement Mobile Money.
Pour le projet, on simule les appels aux API T-Money et Floz.
"""

import random
import uuid
from datetime import datetime


class MobileMoneySimulator:
    """
    Simulateur de paiement Mobile Money.
    """
    
    @classmethod
    def process_payment(cls, phone_number, amount, method):
        """
        Simule un paiement Mobile Money.
        
        Args:
            phone_number: Numéro de téléphone du client
            amount: Montant à payer
            method: TMONEY ou FLOZ
        
        Returns:
            dict: Résultat de la simulation
        """
        # Simulation d'un délai de traitement
        import time
        time.sleep(2)  # Simule le temps de réponse de l'API
        
        # 80% de chance de succès, 20% d'échec
        success = random.random() < 0.8
        
        if success:
            return {
                'success': True,
                'transaction_id': f"{method}_TXN_{uuid.uuid4().hex[:12].upper()}",
                'provider_reference': f"REF{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'message': 'Paiement effectué avec succès',
                'timestamp': datetime.now().isoformat()
            }
        else:
            failures = [
                'Solde insuffisant',
                'Temps d\'attente dépassé',
                'Service temporairement indisponible',
                'Numéro de téléphone invalide',
                'Limite de transaction dépassée'
            ]
            
            return {
                'success': False,
                'transaction_id': None,
                'provider_reference': None,
                'message': random.choice(failures),
                'timestamp': datetime.now().isoformat()
            }
    
    @classmethod
    def check_balance(cls, phone_number):
        """
        Simule la vérification de solde.
        """
        # Solde aléatoire entre 5000 et 50000
        balance = random.randint(5000, 50000)
        return {
            'phone_number': phone_number,
            'balance': balance,
            'currency': 'XOF',
            'timestamp': datetime.now().isoformat()
        }
    
    @classmethod
    def refund_payment(cls, transaction_id, amount):
        """
        Simule un remboursement.
        """
        # 95% de chance de succès
        success = random.random() < 0.95
        
        if success:
            return {
                'success': True,
                'refund_id': f"REFUND_{uuid.uuid4().hex[:12].upper()}",
                'message': 'Remboursement effectué avec succès',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': 'Le remboursement a échoué. Contactez le support.',
                'timestamp': datetime.now().isoformat()
            }