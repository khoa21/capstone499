import hashlib
from hashlib import sha256
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request


class BookCoin:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # new block#
        self.new_book(previous_hash='1', proof=100)
    #adding new node to the list of nodes
    def register_node(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # accept URL
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('invalid URL')

    # validation algo, checking if bc is valid
    def validate(self, chain):

        last_book = chain[0]
        current_index = 1

        while current_index < len(chain):
            book = chain[current_index]
            print(f'{last_book}')
            print(f'{book}')
            print("\n-----------\n")

            # check if last block is correct
            last_book_hash = self.hash(last_book)
            if book['previous_hash'] != last_book_hash:
                return False

            # check if pow is correct
            if not self.valid_proof(last_book['proof'], book['proof'], last_book_hash):
                return False

            last_book = book
            current_index += 1
        return True

    # consensus algo
    def consensus_algo(self):
        # replacing chain with the longest found chain in network
        neighbors = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.validate(chain):
                    max_length = length
                    new_chain = chain

            # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_book(self, proof, previous_hash):
        book = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),

        }
        # reset current list of trans
        self.current_transactions = []

        self.chain.append(book)
        return book
        # transaction block#

    def new_transactions(self, sender, receiver, amount):
        self.current_transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
        })
        return self.last_book['index'] + 1  # the index of the current book + 1


    @property
    def last_book(self):
        return self.chain[-1]

    @staticmethod
    def hash(book):
        book_string = json.dumps(book, sort_keys=True).encode()
        return hashlib.sha256(book_string).hexdigest()

    # proof of work algo#
    def proof_of_work(self, last_book):
        last_proof = last_book['proof']
        last_hash = self.hash(last_book)
        proof = 0

        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof = proof + 1

        return proof

    @staticmethod #validating proof
    def valid_proof(last_proof, proof, last_hash):
        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"



# flask
app = Flask(__name__)
# instantiate the book
bc = BookCoin()
# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')


@app.route('/', )
def starting_page():
    return "<p>Yerrr welcome to book bartering </p>"


@app.route('/mine', methods=['GET'])
def mine():
    # running pow to get to the next proof
    last_book = bc.last_book
    proof = bc.proof_of_work(last_book)

    # reward for finding proof give 1 book
    bc.new_transactions(
        sender="0",
        receiver=node_identifier,
        amount=1,
    )

    # forging new blocks and adding to the chain
    previous_hash = bc.hash(last_book)
    book = bc.new_book(proof, previous_hash)
    response = {
        'message': "New block mined!",
        'index': book['index'],
        'transactions': book['transactions'],
        'proof': book['proof'],
        'previous_hash': book['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def fullchain():
    response = {
        'chain': bc.chain,
        'length': len(bc.chain),
    }
    return jsonify(response), 200


@app.route('/transaction/new', methods=['POST'])
def new_transaction(self):
    values = request.get_json()
    required = ['sender', 'receiver', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

        # new transact
    index = bc.new_transactions(values['sender'], values['receiver'], values['amount'])

    response = {'message': f'transaction {index}'}
    return jsonify(response), 201


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')

    if nodes is None:
        return "no nodes found. please add", 400

    for node in nodes:
        bc.register_node(node)

    response = {
        'message': 'added new nodes successfully!',
        'total_nodes': list(bc.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = bc.consensus_algo()

    if replaced:
        response = {
            'message': 'chain replaced',
            'new_chain': bc.chain
        }
    else:
        response = {
            'message': 'chain is authorized',
            'chain': bc.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
