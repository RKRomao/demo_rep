#dado um intrevalo e um numero n  no intrevalo de 1 a 10000 adivinhar em 10 tentativas onde ele esta.
#o valor introdozido é aleatorio entre 1 e 10000 e em cada tentativa o valor é introdozido pelo usuario e mostra se esta maior ou menor que o valor introdozido.
#como programar a resolução desse problema utilizando python

import random
numero = random.randint(1, 10000)
tentativas = 0
while tentativas < 10:
    numero = int(input("Digite um numero entre 1 e 10000: "))
    tentativas += 1
    if numero == numero:
        print("Parabens, voce acertou em ", tentativas, " tentativas")
        break
    elif numero < numero:
        print("O numero e maior")
    else:
        print("O numero e menor")

#solução
#use o melhor algoritimmo para resolver isso
#busa binaria

def busca_binaria(lista, alvo):
    inicio = 0
    fim = len(lista) - 1
    
    while inicio <= fim:
        meio = (inicio + fim) // 2
        if lista[meio] == alvo:
            return meio
        elif lista[meio] < alvo:
            inicio = meio + 1
        else:
            fim = meio - 1
    
    return -1
