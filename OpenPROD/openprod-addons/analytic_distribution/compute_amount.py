# -*- coding: utf-8 -*-


def compute_amount(type, value, price=0.0):
    """
        Permet de calculer le montant d'une ligne de distribution analytique
        :param type: Type de la distribution
        :type type: char
        :param value: Valeur de la distribution
        :type value: float
        :param price: Prix total sur lequel on veut calculer la distribution
        :type price: float
        :return: Le montant de la ligne de distribution analytique
        :rtype: float
    """
    if type == 'fixed':
        res = value
    elif type == 'percentage':
        res = (value * price) / 100
    else:
        res = 0.0
        
    return res