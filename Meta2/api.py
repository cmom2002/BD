from configparser import ConfigParser
from hashlib import new
import json
from math import prod
from operator import ne
from os import strerror
from random import random, randint
from select import select
from tkinter import INSERT
from flask import Flask, jsonify, request, session, render_template
from functools import wraps
from datetime import datetime, timedelta
import datetime
import logging, psycopg2, time, jwt


app = Flask(__name__)

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500
}

##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    db = psycopg2.connect(
        user = "postgres",
        password = "postgres",
        host = "localhost",
        port = "5432",
        database = "projeto"
    )
    
    return db
    
app.config['SECRET_KEY'] = 'authentication'

#endpoints 
###############################################################################
#                                   endpoints
###############################################################################
@app.route("/")
def landing():
    return jsonify("welcome buddy")


###############################################################################
#                                   register
###############################################################################
@app.route('/dbproj/user', methods=['POST'])
def register():

    #vai buscar argumentos do body
    input = request.get_json()
    
    #tenta conectar à db
    conn = db_connection()

    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)

    cur = conn.cursor()

    newId = geradorIds("id_user", "utilizadores")
    userid_code = request.headers.get('authToken')


    try:

        if userid_code is None: #se nenhum utilizador estiver registado

            params = checkBody(input, {'username', 'email', 'password', 'morada'})
            if params == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
                return jsonify(response)
            
            inputcheck = checkInput([input['username'], input['email'], input['password'], input['morada']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)
            
            repetidos = checkusermail(input['username'], input['email'])

            if repetidos != 0:
                response = {'status': StatusCodes['internal_error'], 'errors': f'Username/Email already in database!'}
                return jsonify(response)

            cur.execute('INSERT INTO utilizadores (id_user, username, email, password, administrador, morada) VALUES (%s, %s, %s, %s, %s, %s)', (newId, input['username'], input['email'], input['password'], False, input['morada']))
            
            cur.execute('INSERT INTO comprador (tem_cupao, utilizadores_id_user) VALUES (%s, %s)', (False, newId))
            
            conn.commit()
            response = {'status': StatusCodes['success'], 'results': f'Inserted comprador {input["username"]}'}
            return jsonify(response)

        else: #se um user ja estiver registado

            userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #descodificar token e ver se user é admin
            cur.execute("SELECT administrador FROM utilizadores where id_user = '%s'" % (userid['userID']))
            isAdmin = cur.fetchall()

            if isAdmin[0][0] == False: #se nao for admin nao pode registar users

                response = {'status': StatusCodes['internal_error'], 'errors': f'User is not an admin!'}
                return jsonify(response) 

            else: #se for admin

                vendedor = checkBody(input, {'username', 'email', 'password', 'morada', 'empresa', 'nif'})
                admin = checkBody(input, {'username', 'email', 'password', 'morada'})

                if vendedor == True: #se quiser registar vendedor 

                    inputcheck = checkInput([input['username'], input['email'], input['password'], input['morada'], input['empresa'], input['nif']])
                    if inputcheck == False:
                        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                        return jsonify(response)

                    repetidos = checkusermail(input['username'], input['email'])

                    if repetidos != 0:
                        response = {'status': StatusCodes['internal_error'], 'errors': f'Username/Email already in database!'}
                        return jsonify(response)

                    cur.execute('INSERT INTO utilizadores (id_user, username, email, password, administrador, morada) VALUES (%s, %s, %s, %s, %s, %s)', (newId, input['username'], input['email'], input['password'], False, input['morada']))
            
                    cur.execute('INSERT INTO vendedor (empresa, nif, utilizadores_id_user) VALUES (%s, %s, %s)', (input['empresa'], input['nif'], newId))

                    conn.commit()
                    response = {'status': StatusCodes['success'], 'results': f'Inserted vendedor {input["username"]}'}
                    return jsonify(response)

                elif admin == True:

                    inputcheck = checkInput([input['username'], input['email'], input['password'], input['morada']])
                    if inputcheck == False:
                        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                        return jsonify(response)

                    repetidos = checkusermail(input['username'], input['email'])

                    if repetidos != 0:
                        response = {'status': StatusCodes['internal_error'], 'errors': f'Username/Email already in database!'}
                        return jsonify(response)

                    cur.execute('INSERT INTO utilizadores (id_user, username, email, password, administrador, morada) VALUES (%s, %s, %s, %s, %s, %s)', (newId, input['username'], input['email'], input['password'], True, input['morada']))
                    conn.commit()
                    response = {'status': StatusCodes['success'], 'results': f'Inserted admin {input["username"]}'}
                    return jsonify(response)

                else:
                    response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
                    return jsonify(response)

    except (Exception, psycopg2.DatabaseError) as error:

        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        return jsonify(response)

    finally:
        if conn is not None:
            conn.close()

  

###############################################################################
#                                   login
###############################################################################

@app.route('/dbproj/user', methods=['PUT'])
def login():

    #vai buscar argumentos do body
    input = request.get_json()

    #tenta conectar à db
    conn = db_connection()

    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)

    cur = conn.cursor()

    params = checkBody(input, {'username', 'password'})

    if params == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
        return jsonify(response)
    
    inputcheck = checkInput([input['username'], input['password']])
    if inputcheck == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
        return jsonify(response)
            

    try:
        cur.execute("SELECT id_user, password FROM Utilizadores WHERE username='%s'"% (input['username']))
        getLog = cur.fetchall()
        #print(getLog)

        if getLog == []:
            response = {'status': StatusCodes['internal_error'], 'errors': 'User not registered!'}
            return jsonify(response)


        if getLog[0][1] != input['password']:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong password!'}
            return jsonify(response)
        
        session['logged_in'] = True
        authToken = jwt.encode({'userID': getLog[0][0], 'exp': datetime.datetime.now() + timedelta(seconds=3600)}, app.config['SECRET_KEY'])
        #print(jwt.decode(authToken, app.config['SECRET_KEY'], algorithms="HS256"))

        cur.close()
        conn.commit()

        return jsonify({"authToken": authToken})


    except (Exception, psycopg2.DatabaseError) as error:
        # logger.error(f'POST /departments - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        # an error occurred, rollback
        conn.rollback()
    return jsonify(response)


###############################################################################
#                                   adidionar produto
###############################################################################

@app.route('/dbproj/product', methods=['POST'])
def adicionar_produto():

    input = request.get_json() # vai buscar argumentos do body

    conn = db_connection() #tenta conectar à bd

    if conn is None:
        out = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(out)

    cur = conn.cursor()
    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM vendedor WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um seller 
    id_vendedor = cur.fetchall()

    if id_vendedor == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a seller!'}
        return jsonify(out)

    pc = checkBody(input, {'nome', 'descricao', 'preco', 'stock', 'processador'})
    tv = checkBody(input, {'nome', 'descricao', 'preco', 'stock', 'tamanho'})
    phone = checkBody(input, {'nome', 'descricao', 'preco', 'stock', 'SO'})

    newId = geradorIds("id_prod", "produtos")

    try:
        if pc:
            inputcheck = checkInput([input['nome'], input['descricao'], input['preco'], input['stock'], input['processador']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)

            cur.execute('INSERT INTO produtos (id_prod, nome, descricao, preco, stock, vendedor_utilizadores_id_user) VALUES (%s, %s, %s, %s, %s, %s)', (newId, input['nome'], input['descricao'], input['preco'], input['stock'], userid['userID']))
            cur.execute('INSERT INTO pc (processador, produtos_id_prod) VALUES (%s, %s)', (input['processador'], newId))
            conn.commit()
            response = {'status': StatusCodes['success'], 'results': f'Inserted product pc: {input["nome"]}'}
            return jsonify(response)
        
        if tv:
            inputcheck = checkInput([input['nome'], input['descricao'], input['preco'], input['stock'], input['tamanho']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)
            cur.execute('INSERT INTO produtos (id_prod, nome, descricao, preco, stock, vendedor_utilizadores_id_user) VALUES (%s, %s, %s, %s, %s, %s)', (newId, input['nome'], input['descricao'], input['preco'], input['stock'], userid['userID']))
            cur.execute('INSERT INTO tv (tamanho, produtos_id_prod) VALUES (%s, %s)', (input['tamanho'], newId))
            conn.commit()
            response = {'status': StatusCodes['success'], 'results': f'Inserted product tv {input["nome"]}'}
            return jsonify(response)

        if phone:
            inputcheck = checkInput([input['nome'], input['descricao'], input['preco'], input['stock'], input['SO']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)

            cur.execute('INSERT INTO produtos (id_prod, nome, descricao, preco, stock, vendedor_utilizadores_id_user) VALUES (%s, %s, %s, %s, %s, %s)', (newId, input['nome'], input['descricao'], input['preco'], input['stock'], userid['userID']))
            cur.execute('INSERT INTO phone (SO, produtos_id_prod) VALUES (%s, %s)', ((input['SO']), newId))
            conn.commit()
            response = {'status': StatusCodes['success'], 'results': f'Inserted product phone {input["nome"]}'}
            return jsonify(response)
        else:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
            return jsonify(response)


    except psycopg2.DataError as e:
        out = {'status': StatusCodes['api_error'], 'errors': 'DataBase Exception'}
        return jsonify(out)

###############################################################################
#                              atualizar produto
###############################################################################

@app.route('/dbproj/product/<product_id>', methods=['PUT'])
def atualizar_produto(product_id):

    input = request.get_json() #ler

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM vendedor WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um seller 
    id_vendedor = cur.fetchall()

    if id_vendedor == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a seller!'}
        return jsonify(out)

    newId = geradorIds("id_hist", "historico")

    try:
        pc = checkBody(input, {'nome', 'descricao', 'preco', 'stock', 'processador'}) #verificar inputs body
        tv = checkBody(input, {'nome', 'descricao', 'preco', 'stock', 'tamanho'})
        phone = checkBody(input, {'nome', 'descricao', 'preco', 'stock', 'SO'})

        if not pc and not tv and not phone:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
            return jsonify(response)

        
        tipoProduto = tipoProd(product_id)

        cur.execute('SELECT * FROM produtos WHERE id_prod = %s'% (product_id)) #se input for valido, selecionar info do produto 
        produto = cur.fetchall()

        if produto == []:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Product does not exist'}
            return jsonify(response)
        #print(produto)
        if produto[0][5] != userid['userID']:
            response = {'status': StatusCodes['internal_error'],'errors': 'This product is not yours'}
            return jsonify(response)

        #print(tipoProduto)
        #print(tv, pc, phone)

    ##Inserir o produto que vai ser atualizado no historico
        timestamp = datetime.datetime.now()
        
        
        if tipoProduto == 'tv' and tv:
            inputcheck = checkInput([input['nome'], input['descricao'], input['preco'], input['stock'], input['tamanho']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)

            cur.execute('select tamanho from tv where produtos_id_prod = %s' % (product_id)) #consoante o tipo do produto, selecionar a spec 
            tamanho = cur.fetchall()
            cur.execute('insert into historico (id_hist, preco, descricao, especificacoes, data, produtos_id_prod) VALUES (%s, %s, %s, %s, %s, %s)', (newId, produto[0][3], produto[0][2], tamanho[0][0], timestamp, product_id))
            cur.execute(f"UPDATE tv SET tamanho = %s WHERE produtos_id_prod = %s", (input['tamanho'], product_id)) 

        elif tipoProduto == 'pc' and pc:
            inputcheck = checkInput([input['nome'], input['descricao'], input['preco'], input['stock'], input['processador']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)

            cur.execute('select processador from pc where produtos_id_prod = %s' % (product_id))
            processador = cur.fetchall()
            cur.execute('insert into historico (id_hist, preco, descricao, especificacoes, data, produtos_id_prod) VALUES (%s, %s, %s, %s, %s, %s)', (newId, produto[0][3], produto[0][2], processador[0][0], timestamp, product_id))
            cur.execute(f"UPDATE pc SET processador = %s WHERE produtos_id_prod = %s", (input['processador'], product_id))

        elif tipoProduto == 'phone' and phone:
            inputcheck = checkInput([input['nome'], input['descricao'], input['preco'], input['stock'], input['SO']])
            if inputcheck == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
                return jsonify(response)
                
            cur.execute('select so from phone where produtos_id_prod = %s' % (product_id))
            so = cur.fetchall()
            cur.execute('insert into historico (id_hist, preco, descricao, especificacoes, data, produtos_id_prod) VALUES (%s, %s, %s, %s, %s, %s)', (newId, produto[0][3], produto[0][2], so[0][0], timestamp, product_id))
            cur.execute(f"UPDATE phone SET so = %s WHERE produtos_id_prod = %s", (input['SO'], product_id))
        
        else:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
            return jsonify(response)

        #atualizar produto

        cur.execute(f"UPDATE produtos SET nome = %s WHERE id_prod = %s", (input['nome'], product_id))
        cur.execute(f"UPDATE produtos SET descricao = %s WHERE id_prod = %s", (input['descricao'], product_id))
        cur.execute(f"UPDATE produtos SET preco = %s WHERE id_prod = %s", (input['preco'], product_id))
        cur.execute(f"UPDATE produtos SET stock = %s WHERE id_prod = %s", (input['stock'], product_id))
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Poduct {input["nome"]} updated'}
        return jsonify(response)


    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)

###############################################################################
#                                   compra
###############################################################################
@app.route('/dbproj/order', methods=['POST'])
def compra():

    input = request.get_json() #ler

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM comprador WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um comprador 
    
    id_comprador = cur.fetchall()

    if id_comprador == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a buyer!'}
        return jsonify(out)

    newId = geradorIds("id_enc", "encomendas")

    params = checkBody(input, {"cart", "cupao"})

    if not params:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
        return jsonify(response)

    inputcheck = checkInput([input['cart'], input['cupao']])
    if inputcheck == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
        return jsonify(response)

    try:
        preco = 0 #criar nova encomenda

        if input['cart'] == []:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Your cart is empty!'}
            return jsonify(response)

        cur.execute("INSERT INTO encomendas (id_enc, preco_total, cupao, data, comprador_utilizadores_id_user) VALUES (%s, %s, %s, %s, %s)", (newId, preco, False, datetime.datetime.now(), userid['userID']))
 
        for produto in input['cart']: #verifica se os produtos existem e se o montante a adquirir nao excede stock

            prod = produto[0]
            quantidade = produto[1]

            cur.execute("select id_prod, stock, preco from produtos where id_prod = %s" % (prod))
            aux = cur.fetchall()
            if not aux:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Product does not exist!'}
                return jsonify(response)

            if aux[0][1] < quantidade:
                response = {'status': StatusCodes['internal_error'], 'errors': 'Amount ordered exceeds stock'}
                return jsonify(response)

            preco = preco + quantidade * aux[0][2]
            #adicionar produtos à lista de produtos e update stock produto

            cur.execute("update produtos set stock = %s where id_prod = %s", ((aux[0][1]-quantidade), prod))

            idlistaprods = geradorIds("id_lista_prods", "lista_prods")
            cur.execute("insert into lista_prods (id_lista_prods, quantidade, encomendas_id_enc, produtos_id_prod) values(%s, %s, %s, %s)", (idlistaprods, quantidade, newId, prod))
        
        #dar update do preço da encomenda

        if input['cupao'] != 'none':

            #print(input['cupao']) #8568
            cur.execute("select tem_cupao from comprador where utilizadores_id_user = '%s'"% (userid['userID'])) #ver se o comprador tem cupao
            tem_cupao = cur.fetchall()

            if tem_cupao[0][0] == False:
                response = {'status': StatusCodes['internal_error'], 'errors': 'User does not own any cupons at the moment'}
                return jsonify(response)

            cur.execute(f"select campanha_id_camp, id_cup from cupao where id_cup = '%s' and comprador_utilizadores_id_user = '%s' and usado = False" % (input['cupao'], userid['userID'])) #ver se o comprador possui o cupao e se ainda nao foi usado
            cupao = cur.fetchall()
          
            if cupao == [] or (int(input['cupao']) != cupao[0][1]):
                response = {'status': StatusCodes['internal_error'], 'errors': 'Invalid cupon/User doesnt own this cupon/Cupon has been used already'}
                return jsonify(response)
            
            cur.execute("select data_aquisicao from cupao where id_cup = '%s'"%(cupao[0][1]))#ver se o cupao é valido 
            data = cur.fetchall()
            cur.execute(f"select validade from campanha where id_camp = '%s'" % (cupao[0][0]))
            validade = cur.fetchall()
            time_change = datetime.timedelta(days=validade[0][0])
            new_time = data[0][0] + time_change

            if new_time < datetime.datetime.now():
                cur.execute("update cupao set expirado = true where id_cup = '%s'" % (cupao[0][1]))
                cur.execute("update comprador set tem_cupao = false where utilizadores_id_user = '%s'" % (userid['userID']))
                conn.commit()
                response = {'status': StatusCodes['internal_error'], 'errors': 'Expired cupon'}
                return jsonify(response)
            

            cur.execute(f"select desconto from campanha where id_camp = '%s'"% (cupao[0][0])) #caso tenha o cupao, ver o desconto correspondente à campanha do cupao
            desconto = cur.fetchall()
            preco = preco - (preco * desconto[0][0] / 100) #aplicar desconto
            cur.execute("update comprador set tem_cupao = False where utilizadores_id_user = '%s'"% (userid['userID'])) #atualizar tabela de comprador para liberar espaço do cupao
            cur.execute("update cupao set usado = True where id_cup = '%s'" % (cupao[0][1])) # atualizar estado usado na tabela de cupoes 

        cur.execute("update encomendas set preco_total = %s where id_enc = %s", (preco, newId))
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Purchase made!'}
        return jsonify(response)

    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)


###############################################################################
#                                   rating
###############################################################################

@app.route("/dbproj/rating/<product_id>", methods=['POST'])
def rating(product_id):
    
    input = request.get_json() #ler

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM comprador WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um comprador 
    id_comprador = cur.fetchall()

    if id_comprador == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a buyer!'}
        return jsonify(out)

    params = checkBody(input, {"rating", "comment"})

    if not params:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
        return jsonify(response)

    inputcheck = checkInput([input['rating'], input['comment']])
    if inputcheck == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
        return jsonify(response)
        
    try:
        #print((userid['userID']))
        cur.execute("select id_enc from encomendas where comprador_utilizadores_id_user = %s"% (userid['userID'])) # selecionar encomendas que tenham o user id do token
        encomendas = cur.fetchall()
        #print(encomendas)

        if encomendas == []: 
            response = {'status': StatusCodes['internal_error'],'errors': 'User has not bought anything'}
            return jsonify(response)
    
        for encomenda in encomendas: #percorrer as encomendas
            cur.execute("select produtos_id_prod from lista_prods where encomendas_id_enc = %s", encomenda) # selecionar os produtos que tenham a o id da encomenda a verificar 
            produtos = cur.fetchall()
            
            
            for produto in produtos: # percorrer os produtos

                if int(produto[0]) == int(product_id): # se o produto se encontrar na lista
                    #print("tou aqui")
                    if int(input['rating']) < 1 or int(input['rating']) > 5: # ver se o rating é valido
                        response = {'status': StatusCodes['internal_error'],'errors': 'Invalid rating'}
                        return jsonify(response) 
                    cur.execute("select comprador_utilizadores_id_user from classificacao where comprador_utilizadores_id_user = %s and produtos_id_prod = %s", (userid['userID'], produto)) # ver se comprador ja esta na lista de classificaçoes desse produto
                    done = cur.fetchall()

                    if done: # ver se o user ja deixou rating/comment
                        response = {'status': StatusCodes['internal_error'],'errors': 'User already rated this product'}
                        return jsonify(response)
                    
                    cur.execute("insert into classificacao (classificacao, comentario, comprador_utilizadores_id_user, produtos_id_prod) VALUES (%s, %s, %s, %s)",(input['rating'], input['comment'], userid['userID'], product_id))
                    conn.commit()
                    response = {'status': StatusCodes['success'], 'results': f'Rating made!'}
                    return jsonify(response)

        response = {'status': StatusCodes['success'], 'results': f'User did not buy this product, therefore cannot review it'}
        return jsonify(response)
                       


    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)  


###############################################################################
#                                  perguntas
###############################################################################

@app.route("/dbproj/questions/<product_id>", methods=['POST'])
def perguntas(product_id):
    input = request.get_json() #ler

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM comprador WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um comprador 
    id_comprador = cur.fetchall()

    if id_comprador == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a buyer!'}
        return jsonify(out)

    params = checkBody(input, {"question"})

    if not params:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
        return jsonify(response)

    inputcheck = checkInput([input['question']])
    if inputcheck == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
        return jsonify(response)

    newId = geradorIds("id_qa", "qa")

    try:    #criar pergunta. qualquer user pode criar uma pergunta 

        cur.execute("insert into qa (id_qa, texto, qa_id_qa, comprador_utilizadores_id_user, produtos_id_prod) values(%s, %s, %s, %s, %s)", (newId, input['question'], 0, userid['userID'], product_id))
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Question/Comment Done!'}
        return jsonify(response)
        
    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)  

@app.route("/dbproj/questions/<product_id>/<parent_question_id>", methods=['POST'])
def perguntas2(product_id, parent_question_id):
    input = request.get_json() #ler

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM comprador WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um comprador 
    id_comprador = cur.fetchall()

    if id_comprador == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a buyer!'}
        return jsonify(out)

    params = checkBody(input, {"question"})

    if not params:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
        return jsonify(response)

    inputcheck = checkInput([input['question']])
    if inputcheck == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
        return jsonify(response)

    newId = geradorIds("id_qa", "qa")

    try:    #criar pergunta. qualquer user pode criar uma pergunta 

        cur.execute("insert into qa (id_qa, texto, qa_id_qa, comprador_utilizadores_id_user, produtos_id_prod) values(%s, %s, %s, %s, %s)", (newId, input['question'], parent_question_id, userid['userID'], product_id))
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Question/Comment Done!'}
        return jsonify(response)
        
    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)  

###############################################################################
#                                 consulta
###############################################################################

@app.route("/dbproj/product/<product_id>", methods=['GET'])
def consulta(product_id):

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM comprador WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um comprador 
    id_comprador = cur.fetchall()

    if id_comprador == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a buyer!'}
        return jsonify(out)
    
    try:
        print(type(product_id))
        print(product_id)
        cur.execute("select id_prod from produtos where id_prod = %s" % (product_id))
        existe = cur.fetchall()

        if existe == []:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Product does not exist'}
            return jsonify(response)
        
        cur.execute(f"""SELECT produtos.nome, produtos.descricao,round(avg(classificacao.classificacao),1) as "rating medio", string_agg(classificacao.comentario,'; ') as "comentarios", string_agg(cast(historico.preco as varchar),'; ') as "precos"
                        from produtos
                        Left join historico on historico.produtos_id_prod = %s 
                        Left join classificacao on classificacao.produtos_id_prod = %s 
                        where produtos.id_prod = %s 
                        group by produtos.nome, produtos.descricao"""% (int(product_id), int(product_id), int(product_id)))
        resultado = cur.fetchall()
        print(resultado)
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Product details:{resultado}'}
        return jsonify(response)
        
    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)  

###############################################################################
#                                   criar campanha
###############################################################################

@app.route("/dbproj/campaign", methods=['POST'])
def criar_campanha():
    
    input = request.get_json() #ler

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT id_user FROM utilizadores WHERE id_user = %s and administrador = True" % (userid['userID'])) #verificar se o user é um admin 
    id_admin = cur.fetchall()

    if id_admin == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not an admin!'}
        return jsonify(out)

    params = checkBody(input, {"descricao","data_inicio","data_fim","numero_cupoes","desconto","validade"})

    if not params:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing params!'}
        return jsonify(response)

    inputcheck = checkInput([input['descricao'], input['data_inicio'], input['data_fim'], input['numero_cupoes'], input['desconto'], input['validade']])
    if inputcheck == False:
        response = {'status': StatusCodes['internal_error'], 'errors': 'Wrong/missing input!'}
        return jsonify(response)

    newId = geradorIds("id_camp", "campanha")

    try:        
        cur.execute("SELECT id_camp FROM campanha WHERE data_fim >= '%s'" % (datetime.datetime.now()))
        limite = cur.fetchall()
        if limite != []:
            out = {'status': StatusCodes['internal_error'], 'errors': 'Cannot create, there is an ongoing campaign'}
            return jsonify(out) 
        
        #verificar se a data fim ja passou 
        
        cur.execute('INSERT INTO campanha (id_camp, descricao, data_inicio, data_fim, validade, numero_cupoes, desconto, utilizadores_id_user) VALUES (%s, %s, %s, %s, %s, %s, %s,%s)', (newId, input['descricao'], input['data_inicio'], input['data_fim'],input['validade'], input['numero_cupoes'],input['desconto'], userid['userID']))
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Campain created!'}
        return jsonify(response)        
        
    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)

###############################################################################
#                                   subscrever_campanha
###############################################################################

@app.route("/dbproj/subscribe/<campaign_id>", methods=['PUT'])
def subscrever_campanha(campaign_id):

    conn = db_connection()#conectar bd
    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)
    cur = conn.cursor()

    userid_code = request.headers.get('authToken') # le o token

    if userid_code is None: #verificar se user esta logged in 
        out = {'status': StatusCodes['internal_error'], 'errors': 'User not logged in'}
        return jsonify(out)

    userid = jwt.decode(userid_code, app.config['SECRET_KEY'], algorithms="HS256") #se estiver, descodificar

    cur.execute("SELECT utilizadores_id_user FROM comprador WHERE utilizadores_id_user = '%s'" % (userid['userID'])) #verificar se o user é um comprador 
    id_comprador = cur.fetchall()

    if id_comprador == []:
        out = {'status': StatusCodes['internal_error'], 'errors': 'User is not a buyer!'}
        return jsonify(out)

    try:
        cur.execute("SELECT id_camp FROM campanha WHERE id_camp = %s and data_fim >= %s", (campaign_id, datetime.datetime.now())) #verificar se campanha ainda nao terminou
        id_camp = cur.fetchall()

        if id_camp == []:
            out = {'status': StatusCodes['internal_error'], 'errors': 'Campaign is over or does not exist!'}
            return jsonify(out)

        cur.execute("SELECT tem_cupao FROM comprador WHERE utilizadores_id_user = %s" % (userid['userID'])) #verificar se user ja tem um cupao
        tem_cupao = cur.fetchall()
  
        if tem_cupao[0][0] == True: #se tiver cupao

            cur.execute("select id_cup from cupao where campanha_id_camp = '%s' and comprador_utilizadores_id_user = '%s' and usado = 'False' and expirado = 'False'"% (campaign_id, userid['userID']))
            cupao = cur.fetchall()

            cur.execute("select data_aquisicao from cupao where id_cup = '%s'"%(cupao[0][0]))#ver se o cupao é valido 
            data = cur.fetchall()

            cur.execute(f"select validade from campanha where id_camp = '%s'" % (campaign_id))
            validade = cur.fetchall()
            time_change = datetime.timedelta(days=validade[0][0])
            new_time = data[0][0] + time_change
            
            if new_time >= datetime.datetime.now(): #se for valido 
                response = {'status': StatusCodes['internal_error'], 'errors': 'User already has cupon'}
                return jsonify(response)

            cur.execute("update cupao set expirado = 'True' where id_cup = '%s'" % (cupao[0][0]))
            response = {'status': StatusCodes['success'], 'results': f'Cupon aquired!'}
        
        cur.execute("SELECT numero_cupoes FROM campanha where id_camp = %s"% (campaign_id)) #ver se a campanha ainda tem cupoes 
        num_cupoes = cur.fetchall()
        if num_cupoes[0][0] <= 0:

            out = {'status': StatusCodes['internal_error'], 'errors': 'No more cupons available in this campaign'}
            return jsonify(out)
        #print(num_cupoes)
        #print(num_cupoes[0][0])
        ncup = num_cupoes[0][0]  # é removido um cupao da campanha
        ncup = ncup - 1
        cur.execute("UPDATE campanha SET numero_cupoes = %s where id_camp = %s", (ncup, campaign_id))

        newId = geradorIds("id_cup", "cupao") # é criado um cupao 

        cur.execute('INSERT INTO cupao (id_cup, data_aquisicao, usado, expirado, comprador_utilizadores_id_user, campanha_id_camp) VALUES (%s,%s, %s, %s, %s, %s)', (newId, datetime.datetime.now(), False,False, userid['userID'], campaign_id))
        cur.execute("UPDATE comprador SET tem_cupao = True where utilizadores_id_user = %s"% (userid['userID']))
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Cupon aquired!'}
   

   
    except psycopg2.Error as e:
        response = {'status': StatusCodes['api_error'], 'errors': str(e)}
        return jsonify(response)  
    return jsonify(response)


###############################################################################
#                                   funçoes auxiliares
###############################################################################


def geradorIds(id, tabela):

    a = True

    conn = db_connection()

    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)

    cur = conn.cursor()
    while a:
        idgerado = randint(10000000, 99999999)
        cur.execute("Select %s from %s where %s=%s" % (id,tabela,id,idgerado))
        test = cur.fetchall()
        if (len(test) == 0):
            a = False
    return idgerado    

def checkBody(body, need):
    #print(body)
    #print(need)
    for i in body.keys():
        if i not in need:
            #print("errou no %s", i)
            return False
    for i in need:
        if i not in body.keys():
            #print("errou no %s", i)
            return False
    return True

def checkInput(input):

    for i in input:
        if i == "" or i is None:
            return False
    return True


def checkusermail(username, email):

    conn = db_connection()

    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)

    cur = conn.cursor()
             
    cur.execute("Select username from utilizadores where username='%s'" % (username)) #teste para usernames repetidos
    test = cur.fetchall()

    if len(test) != 0:
        return 1

    cur.execute("Select email from utilizadores where email='%s'" % (email)) #testepara emails repetidos 
    test = cur.fetchall()

    if len(test) != 0:
        return 2
    return 0

def tipoProd(id):

    conn = db_connection()

    if conn is None:
        response = {'status': StatusCodes['api_error'], 'errors': 'Connection to database failed'}
        return jsonify(response)

    cur = conn.cursor()

    cur.execute("select produtos_id_prod from tv where produtos_id_prod = %s" % (id))
    tv = cur.fetchall()
    if tv != []:
        return "tv"

    cur.execute("select produtos_id_prod from pc where produtos_id_prod = %s" % (id))
    pc = cur.fetchall()
    if pc != []:
        return "pc"
        
    cur.execute("select produtos_id_prod from phone where produtos_id_prod = %s" % (id))
    phone = cur.fetchall()
    if phone != []:
        return "phone"

if __name__ == "__main__":
    #works\'
    app.run(debug=True, port = 8080)

    

