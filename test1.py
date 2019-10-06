import time
class Elevator():
    def __init__(self,  DefFloorNum=1):

        self.WeightMax = 500
        self.NumberOfFloor = 10
        self.FloorNum=DefFloorNum
    def run(self):
        n = abs(self.FloorNum - self.NumberOfFloor)
        if  n == 0:
            print (f'Floor #{self.FloorNum} Weight:{self.weight}')
        elif n > 0:
            print (f'Floor #{self.FloorNum} Weight:{self.weight}')
            time.sleep (1)
            try:
                for i in range(0, n):
                    if  self.NumberOfFloor - self.FloorNum  < 0 :
                        self.FloorNum -= 1
                    elif self.NumberOfFloor - self.FloorNum  > 0 :
                        self.FloorNum += 1
                    print (f'Floor #{self.FloorNum} Weight:{self.weight}')
                    time.sleep(1)
                # self.FloorNum = self.NumberOfFloor
            except KeyboardInterrupt:
                print (f"""**************************************************
                Interrupt!!!!!
                We are stop on the floor #{self.FloorNum}""")
    def InputFloor(self):
        Floor = int(input ("Input floor: "))
        if Floor >= 1 and Floor <= 10:
            self.Weight(int(input ("Weight: ")))
            self.NumberOfFloor = Floor
            self.run()

        else:
            print ("Wrong input")
    def Weight (self, weight):
        self.weight = weight
        if weight > 0:
            if self.weight > self.WeightMax:
                print ("Wrong Waigt")
                exit(1)
        if weight < 0:
            if self.weight < 0:
                print ("Wrong Waigt")
                exit(1)


lift  = Elevator(DefFloorNum=1)
lift.InputFloor()
lift.InputFloor()