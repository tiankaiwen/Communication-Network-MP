import sys

def main():
    currInput = "A 10.0.0/23 14A 11.0.0.0/24 14"
    if currInput.count('A') > 2:
        advertise1 = "A" + currInput.split("A")[1]
        advertise2 = "A" + currInput.split("A")[2]
    print(advertise1)
    print(advertise2)
main()
