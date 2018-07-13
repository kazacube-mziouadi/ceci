# -*- coding: utf-8 -*-
'''
Created on 5 juin 2015

@author: sylvain
'''

from openerp import models, fields, api


class product_product(models.Model):
    _inherit = 'product.product'

    def get_price_sale_standard(self, customer, qty):
        """
            Surcharge. Calcule le prix d'un produit suivant les offres standard applicables
        """
        devise_price = customer.currency_id
        net_price_for_customer = self.get_net_price_for_customer(customer, qty)
        if len(net_price_for_customer):
            if devise_price == net_price_for_customer.offer_id.currency_id:
                price = net_price_for_customer.value
            else:
                price = net_price_for_customer.offer_id.currency_id.compute(net_price_for_customer.value, customer.currency_id)
                 
        else:
            base_price, devise_offer = self.get_base_price_all_customers(qty, customer=customer)
            if devise_price != devise_offer:
                base_price = devise_offer.compute(base_price, devise_price)
                
            category_discount_for_customer = self.get_category_discount_for_customer(customer, qty)
            product_discount_for_customer = self.get_product_discount_for_customer(customer, qty)
            if len(product_discount_for_customer):
                product_discount_operator = -1 if product_discount_for_customer.discount_type == "increase" else 1

            if len(category_discount_for_customer):
                category_discount_operator = -1 if category_discount_for_customer.discount_type == "increase" else 1
                if len(product_discount_for_customer):
                    price = base_price * (1 - category_discount_operator * category_discount_for_customer.value / 100.) * (
                        1 - product_discount_operator * product_discount_for_customer.value / 100.)
                else:
                    price = base_price * (1 - category_discount_operator * category_discount_for_customer.value / 100.)
                    
            else:
                if len(product_discount_for_customer):
                    price = base_price * (1 - product_discount_operator * product_discount_for_customer.value / 100.)
                else:
                    price = base_price
            
        return price, devise_price
    

    def get_net_price_for_customer(self, customer, qty):
        standard_offer_line_obj = self.env["standard.offer.line"]
        base_search_arg = [("offer_id.state", "=", "applicable"), ("discount_type", "=", "net_price"), ("quantity", "<=", qty)] + self.between_dates(fields.Date.today())
        customer_search_arg = [("offer_id.type", "=", "customer"), ("offer_id.customer_id", "=", customer.id)]
        search_arg_1 = [("type", "=", "product"), ("product_id", "=", self.id)]
        net_price = standard_offer_line_obj.search(
            customer_search_arg + search_arg_1 + [('currency_id', '=', customer.currency_id.id)] + base_search_arg,
            limit=1,
            order="quantity DESC"
        )
        if not len(net_price):
            company_currency_rc = self.env.user.partner_id and self.env.user.partner_id.currency_id or False
            if company_currency_rc:
                net_price = standard_offer_line_obj.search(
                    customer_search_arg + search_arg_1 + [('currency_id', '=', company_currency_rc.id)] + base_search_arg,
                    limit=1,
                    order="quantity DESC"
                )
                
            if not len(net_price):
                search_arg_2 = [("type", "=", "category"), ("category_id", "=", self.sale_family_id.id)]
                net_price = standard_offer_line_obj.search(
                    customer_search_arg + search_arg_2 + [('currency_id', '=', customer.currency_id.id)] + base_search_arg,
                    limit=1,
                    order="quantity DESC"
                )
                if not len(net_price):
                    if company_currency_rc:
                        net_price = standard_offer_line_obj.search(
                            customer_search_arg + search_arg_2 + [('currency_id', '=', company_currency_rc.id)] + base_search_arg,
                            limit=1,
                            order="quantity DESC"
                        )
                        
                    if not len(net_price) and customer.stat_family_id:
                        family_search_arg = [("offer_id.type", "=", "family"), ("offer_id.family_id", "=", customer.stat_family_id.id)]
                        search_arg_3 = [("type", "=", "product"), ("product_id", "=", self.id)]
                        net_price = standard_offer_line_obj.search(
                            family_search_arg + search_arg_3 + [('currency_id', '=', customer.currency_id.id)] + base_search_arg,
                            limit=1,
                            order="quantity DESC"
                        )
                        if not len(net_price):
                            if company_currency_rc:
                                net_price = standard_offer_line_obj.search(
                                    family_search_arg + search_arg_3 + [('currency_id', '=', company_currency_rc.id)] + base_search_arg,
                                    limit=1,
                                    order="quantity DESC"
                                )
                                
                            if not len(net_price) and self.sale_family_id.id:
                                search_arg_4 = [("type", "=", "category"), ("category_id", "=", self.sale_family_id.id)]
                                net_price = standard_offer_line_obj.search(
                                    family_search_arg + search_arg_4 + [('currency_id', '=', customer.currency_id.id)] + base_search_arg,
                                    limit=1,
                                    order="quantity DESC"
                                )
                                if not len(net_price) and company_currency_rc:
                                    net_price = standard_offer_line_obj.search(
                                        family_search_arg + search_arg_4 + [('currency_id', '=', company_currency_rc.id)] + base_search_arg,
                                        limit=1,
                                        order="quantity DESC"
                                    )
                    
        return net_price
    

    def get_category_discount_for_customer(self, customer, qty):
        base_search_arg = [
                ("offer_id.state", "=", "applicable"),
                ("type", "=", "category"),
                ("discount_type", "in", ["discount", "increase"]),
                ("category_id", "=", self.sale_family_id.id),
                ("quantity", "<=", qty)
        ] + self.between_dates(fields.Date.today())
        category_discount = self.env["standard.offer.line"].search(
            [("offer_id.type", "=", "customer"), ("offer_id.customer_id", "=", customer.id)] + base_search_arg,
            limit=1,
            order="quantity DESC"
        )
        if not category_discount and customer.stat_family_id.id:
            category_discount = self.env["standard.offer.line"].search(
                [("offer_id.type", "=", "family"), ("offer_id.family_id", "=", customer.stat_family_id.id) ] + base_search_arg,
                limit=1,
                order="quantity DESC"
            )
            
        return category_discount
    

    def get_product_discount_for_customer(self, customer, qty):
        standard_offer_line_obj = self.env["standard.offer.line"]
        base_search_arg = [
            ("offer_id.state", "=", "applicable"),
            ("type", "=", "product"),
            ("discount_type", "in", ["discount", "increase"]),
            ("product_id", "=", self.id),
            ("quantity", "<=", qty)
        ] + self.between_dates(fields.Date.today())
        product_discount = standard_offer_line_obj.search(
            [("offer_id.type", "=", "customer"), ("offer_id.customer_id", "=", customer.id)] + base_search_arg,
            limit=1,
            order="quantity DESC"
        )
        if not len(product_discount) and customer.stat_family_id:
            product_discount = standard_offer_line_obj.search(
                [("offer_id.type", "=", "family"), ("offer_id.family_id", "=", customer.stat_family_id.id)] + base_search_arg,
                limit=1,
                order="quantity DESC"
            )
                
        return product_discount
    

    def get_base_price_all_customers(self, qty, customer=False):
        base_price_all_customers = []
        standard_offer_line_obj = self.env["standard.offer.line"]
        base_search_arg = [
            ("offer_id.type", "=", "standard"),
            ("offer_id.state", "=", "applicable"),
            ("discount_type", "=", "base_price"),
            ("quantity", "<=", qty)
        ] + self.between_dates(fields.Date.today())
        search_arg_1 = [("type", "=", "product"), ("product_id", "=", self.id)]
        if customer:                          
            base_price_all_customers = standard_offer_line_obj.search(
                search_arg_1 + [('currency_id', '=', customer.currency_id.id)] + base_search_arg,
                limit=1,
                order="quantity DESC"
            )
            
        if not len(base_price_all_customers):
            company_currency_rc = self.env.user.partner_id and self.env.user.partner_id.currency_id or False
            if company_currency_rc:                                    
                base_price_all_customers = standard_offer_line_obj.search(
                    search_arg_1 + [('currency_id', '=', company_currency_rc.id)] + base_search_arg,
                    limit=1,
                    order="quantity DESC"
                )
            
            if self.sale_family_id.id:
                search_arg_2 = [("type", "=", "category"), ("category_id", "=", self.sale_family_id.id)]
                if not len(base_price_all_customers) and customer:
                    base_price_all_customers = standard_offer_line_obj.search(
                        search_arg_2 + [('currency_id', '=', customer.currency_id.id)] + base_search_arg,
                        limit=1,
                        order="quantity DESC"
                    )
                    
                if not len(base_price_all_customers) and company_currency_rc:
                    base_price_all_customers = standard_offer_line_obj.search(
                        search_arg_2 + [('currency_id', '=', company_currency_rc.id)] + base_search_arg,
                        limit=1,
                        order="quantity DESC"
                    )
                
        if len(base_price_all_customers):
            base_price = base_price_all_customers.value
            devise_price = base_price_all_customers.offer_id.currency_id
        else:
            base_price = self.sale_price
            devise_price = customer and customer.currency_id or False

        return base_price, devise_price
    

    def get_price_sale_for_offer(self, offer, qty):
        """
            Calcul le prix d'un produit d'après une offre particulière + les offres standard applicables
        """
        net_price_for_offer = self.get_net_price_for_offer(offer, qty)
        if len(net_price_for_offer):
            price = net_price_for_offer.value
        else:
            base_price, devise_price = self.get_base_price_all_customers(qty)
            category_discount_for_offer = self.get_category_discount_for_offer(offer, qty)
            product_discount_for_offer = self.get_product_discount_for_offer(offer, qty)
            if len(product_discount_for_offer):
                product_discount_operator = -1 if product_discount_for_offer.discount_type == "increase" else 1
            if len(category_discount_for_offer):
                category_discount_operator = -1 if category_discount_for_offer.discount_type == "increase" else 1
                if len(product_discount_for_offer):
                    price = base_price * (1 - category_discount_operator * category_discount_for_offer.value / 100.) * (
                        1 - product_discount_operator * product_discount_for_offer.value / 100.)
                else:
                    price = base_price * (1 - category_discount_operator * category_discount_for_offer.value / 100.)
            else:
                if len(product_discount_for_offer):
                    price = base_price * (1 - product_discount_operator * product_discount_for_offer.value / 100.)
                else:
                    price = base_price
        return price

    def get_net_price_for_offer(self, offer, qty):
        standard_offer_line_obj = self.env["standard.offer.line"]
        net_price = standard_offer_line_obj.search([
            ("offer_id.id", "=", offer.id), ("type", "=", "product"), ("discount_type", "=", "net_price"), ("product_id", "=", self.id),
            ("quantity", "<=", qty)
        ],
                                                           limit=1,
                                                           order="quantity DESC")
        if not len(net_price):
            net_price = standard_offer_line_obj.search([
                ("offer_id.id", "=", offer.id), ("type", "=", "category"), ("discount_type", "=", "net_price"),
                ("category_id", "=", self.sale_family_id.id), ("quantity", "<=", qty)
            ],
                                                               limit=1,
                                                               order="quantity DESC")
        return net_price

    def get_category_discount_for_offer(self, offer, qty):
        category_discount = self.env["standard.offer.line"].search([
            ("offer_id.id", "=", offer.id), ("type", "=", "category"), ("discount_type", "in", ["discount", "increase"]),
            ("category_id", "=", self.sale_family_id.id), ("quantity", "<=", qty)
        ],
                                                                   limit=1,
                                                                   order="quantity DESC")
        return category_discount

    def get_product_discount_for_offer(self, offer, qty):
        product_discount = self.env["standard.offer.line"].search([
            ("offer_id.id", "=", offer.id), ("type", "=", "product"), ("discount_type", "in", ["discount", "increase"]),
            ("product_id", "=", self.id), ("quantity", "<=", qty)
        ],
                                                                  limit=1,
                                                                  order="quantity DESC")
        return product_discount

    def between_dates(self, date):
        """
            Retourne une partie de domaine : date est compris entre deux dates qui peuvent être vides
        """
        a = ("offer_id.start_date", "<=", date)
        b = ("offer_id.end_date", ">=", date)
        an = ("offer_id.start_date", "=", None)
        bn = ("offer_id.end_date", "=", None)
        return ["|", "&", a, b, "|", "&", a, bn, "|", "&", b, an, "&", an, bn]
