<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <style type="text/css">
            .overflow_ellipsis {
                text-overflow: ellipsis;
                overflow: hidden;
                white-space: nowrap;
            }
            .account_level_1 {
                text-transform: uppercase;
                font-size: 15px;
                background-color:#F0F0F0;
            }

            .account_level_2 {
                font-size: 12px;
                background-color:#F0F0F0;
            }

            .regular_account_type {
                font-weight: normal;
            }

            .view_account_type {
                font-weight: bold;
            }

            .account_level_consol {
                font-weight: normal;
            	font-style: italic;
            }
            .list_table .act_as_row {
                margin-top: 10px;
                margin-bottom: 10px;
                font-size:10px;
            }
            ${css}
        </style>
    </head>
    <body>

        <%setLang(user.lang)%>
        
        <div align="center" style="width: 1300px;">
         	<h1 style="width: 1300px;">Situation des Rapprochements Bancaires AU ${formatLang(period(data).date_stop or '',date=True)}</h1>
        </div>

        </br>
        
        <div class="act_as_table data_table" style="width: 1350px;">
            <div class="act_as_row labels" >
                <div class="act_as_cell" >${_('Code Banque')}</div>
                <!--div class="act_as_cell" >${_('N° Compte Bancaire')}</div-->
                <div class="act_as_cell" >${_('Banque')}</div>
                <div class="act_as_cell" >${_('N° Compte Comptable')}</div>
            </div>
            <div class="act_as_row">
                <div class="act_as_cell" >${ bank(data).bic }</div>
                <!--div class="act_as_cell" >${ bank(data).bic }</div-->
                <div class="act_as_cell" >${ bank(data).name }</div>
                <div class="act_as_cell" >${ account(data).code }</div>
            </div>
        </div>
        
        </br>
        	  <%
              cumul_debit = 0.0
              cumul_credit = 0.0
              cumul_bank_debit =  0.0
              cumul_bank_credit = 0.0
              cumul_bank_rapp_debit =  0.0
              cumul_bank_rapp_credit = 0.0
              %>
        <div class="act_as_table data_table" align="center">
         	<div class="act_as_row labels" align="center">
	            <div class="act_as_cell" style="width: 700px;">${_('Écritures Comptables')}</div>
	            <div class="act_as_cell" style="width: 650px;">${_('Écritures Bancaires')}</div>
	        </div>
       </div>
        <div class="act_as_table data_table" align="center">
           <div class="act_as_thead">
            <div class="act_as_row labels">
                    ## date
                    <div class="act_as_cell first_column" style="width: 100px;">${_('Dt. Opér')}</div>
                    ## libelle
                    <div class="act_as_cell" style="width: 250px;">${_('Libellé')}</div>
                    ## débit
                    <div class="act_as_cell " style="width: 100px;">${_('Débit')}</div>
                    ## crédit
                    <div class="act_as_cell " style="width: 100px;">${_('Crédit')}</div>
                    ## pièce compatable
                    <div class="act_as_cell" style="width: 150px;">${_('Pièce')}</div>
                   	## rapprochement
                    <div class="act_as_cell first_column" style="width: 100px;">${_('Dt. Opér')}</div>
                    ## débit
                    <div class="act_as_cell " style="width: 100px;">${_('Débit')}</div>
                    ## crédit
                    <div class="act_as_cell " style="width: 100px;">${_('Crédit')}</div>
                    ## pièce compatable
                    <div class="act_as_cell" style="width: 350px;">${_('Libellé')}</div>
            </div>
           </div>
            %for line in get_lines(data):
	            <%
                    cumul_debit += line['debit'] or 0.0
                    cumul_credit += line['credit'] or 0.0
                %>			                  
		       	<%
                    if line['amount'] < 0 :
                    	cumul_bank_debit += line['amount'] or 0.0
                    else :
                    	cumul_bank_credit += line['amount'] or 0.0
                %>			                  
            
            	<div class="act_as_row lines">
                      ## date
                      <div class="act_as_cell">${formatLang(line['date'] or '',date=True)}</div>
                      ## libelle
                      <div class="act_as_cell">${line['name'] or ''}</div>
                      ## débit
                      <div class="act_as_cell amount">${line['debit'] or 0.0}</div>
                      ## crédit
                      <div class="act_as_cell amount" >${line['credit'] or 0.0}</div>
                      ## pièce compatable
                      <div class="act_as_cell">${line['piece']}</div>
                      ## date operation bancaire
                      <div class="act_as_cell">${formatLang(line['date_op_bank'] or '',date=True)}</div>
                      %if line['amount'] < 0 :
                      	  ## débit
	                      <div class="act_as_cell amount">${abs(line['amount'])}</div>
	                      ## crédit
	                      <div class="act_as_cell amount" >${0.0}</div>
	                  %else:
	                  	  ## débit
	                      <div class="act_as_cell amount">${0.0}</div>
	                      ## crédit
	                      <div class="act_as_cell amount" >${line['amount']}</div>
	                      ## libelle operation bancaire
                      	  <div class="act_as_cell">${line['libelle']}</div>
                  	  %endif
            	</div>
            %endfor
        </div>
        
        </br>
        <div style="break-line-before: always;">
        <div class="act_as_table data_table" align="center">
            %for line in bank_statement_lines_rapproched(data):
            	<%
                    if line.amount < 0 :
                    	cumul_bank_rapp_debit += line.amount 
                    else :
                    	cumul_bank_rapp_credit += line.amount 
                %>	
            %endfor
    		
    		<div class="act_as_row labels">
                ## Cumul écritures non rapprochées
                <div class="act_as_cell first_column" style="width: 350px;">${_('Cumul écritures non rapprochées')}</div>
                <div class="act_as_cell amount" style="width: 100px;">${cumul_debit}</div>	
	            <div class="act_as_cell amount" style="width: 100px;">${cumul_credit}</div>		
	            <div class="act_as_cell amount" style="width: 150px;">${}</div>	
	           	<div class="act_as_cell amount" style="width: 100px;">${}</div>	    
	            <div class="act_as_cell amount" style="width: 100px;">${cumul_bank_debit}</div>	
	            <div class="act_as_cell amount" style="width: 100px;">${cumul_bank_credit}</div>		
	            <div class="act_as_cell first_column" style="width: 350px;">${_('Cumul écritures bancaires non rapprochées')}</div>
        	</div>
        	<div class="act_as_row labels">
                ## Solde écritures non rapprochées
                <div class="act_as_cell first_column" style="width: 350px;">${_('Solde écritures non rapprochées')}</div>
               	%if cumul_debit - cumul_credit   < 0 :
               		  <div class="act_as_cell amount" style="width: 100px;">${}</div>
	                  <div class="act_as_cell amount" style="width: 100px;">${abs(cumul_debit - cumul_credit)}</div>	
	           	%else:
               		  <div class="act_as_cell amount" style="width: 100px;">${cumul_debit - cumul_credit}</div>
	                  <div class="act_as_cell amount" style="width: 100px;">${}</div>
	            %endif	
	            <div class="act_as_cell" style="width: 150px;">${}</div>	
	           	<div class="act_as_cell" style="width: 100px;">${}</div>	 
	           	
	           	%if cumul_bank_credit - cumul_bank_debit < 0 :
               		  <div class="act_as_cell amount" style="width: 100px;">${abs(cumul_bank_credit - cumul_bank_debit)}</div>
	                  <div class="act_as_cell amount" style="width: 100px;">${0.0}</div>	
	           	%else:
               		  <div class="act_as_cell amount" style="width: 100px;">${0.0}</div>
	                  <div class="act_as_cell amount" style="width: 100px;">${cumul_bank_credit - cumul_bank_debit}</div>	
	            %endif
	            <div class="act_as_cell first_column" style="width: 350px;">${_('Solde écritures bancaires non rapprochées')}</div>
        	</div>
        	<div class="act_as_row labels">
                ## Cumul écritures rapprochées
                <div class="act_as_cell first_column" style="width: 350px;">${_('Cumul écritures rapprochées')}</div>
                <div class="act_as_cell amount" style="width: 100px;">${move_line_debit(data)}</div>	
	            <div class="act_as_cell amount" style="width: 100px;">${move_line_credit(data)}</div>		
	            <div class="act_as_cell amount" style="width: 150px;">${}</div>	
	           	<div class="act_as_cell amount" style="width: 100px;">${}</div>	    
	            <div class="act_as_cell amount" style="width: 100px;">${abs(cumul_bank_rapp_debit)}</div>	
	            <div class="act_as_cell amount" style="width: 100px;">${cumul_bank_rapp_credit}</div>		
	            <div class="act_as_cell first_column" style="width: 350px;">${_('Cumul écritures bancaires rapprochées')}</div>
        	</div>
        	<div class="act_as_row labels">
                ## Nouveau Solde
                <div class="act_as_cell first_column" style="width: 350px;">Nouveau Solde au ${formatLang(period(data).date_stop or '',date=True)}</div>
                %if (move_line_debit(data)+cumul_debit)-(move_line_credit(data)+cumul_credit) < 0 :
	                  <div class="act_as_cell amount" style="width: 100px;">${}</div>	
	                  <div class="act_as_cell amount" style="width: 100px;">${abs((move_line_debit(data)+cumul_debit)-(move_line_credit(data)+cumul_credit))}</div>		
	           	%else:
	                  <div class="act_as_cell amount" style="width: 100px;">${(move_line_debit(data)+cumul_debit)-(move_line_credit(data)+cumul_credit)}</div>	
			<div class="act_as_cell amount" style="width: 100px;">${}</div>
		%endif
	                  <div class="act_as_cell amount" style="width: 100px;">${}</div>		
	            <div class="act_as_cell amount" style="width: 150px;">${}</div>	

               	%if bank_stat(data).balance_end_real < 0 :
	                  <div class="act_as_cell amount" style="width: 100px;">${abs(bank_stat(data).balance_end_real)}</div>	
	                  <div class="act_as_cell amount" style="width: 100px;">${}</div>		
	           	%else:
	                  <div class="act_as_cell amount" style="width: 100px;">${}</div>	
	                  <div class="act_as_cell amount" style="width: 100px;">${bank_stat(data).balance_end_real}</div>		
               	%endif
             	<div class="act_as_cell" style="width: 225px;">Nouveau Solde au ${formatLang(period(data).date_stop or '',date=True)}</div>	                      
        	</div>
        	
        </div>
        </div>
    </body>
</html>





