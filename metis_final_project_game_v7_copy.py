'''
Note: DO NOT CHANGE!!!!

- what program does:
(1) [done] remove all mention of wall states [this is done on previously trained car without walls]
(2) [done] incorporate police car into model [GTA car reacts to police]

- further improvements:
(a) make both police and GTA car go smoother
(b) put breadcrumb to show previous GTA track
(c) incorporate angle transitions

'''
import numpy as np
import random
from sklearn.externals import joblib
import pygame
from pygame.locals import *
import time

def openPickledFiles():
    '''
    function: unpickle the q_matrix and pos, neg, and wall states to be used
    '''
    q_matrix = joblib.load('qMatrix_7by7_no_walls.pkl')
    posState = (6,6)
    negState = (5,5)
    return q_matrix, posState, negState

def makeMoveMatrix(q_matrix, num_rows, num_cols, row_max, col_max, posState, negState):
    '''
    aim: we have to take each row of q-matrix which is a state (4 cols, 4 actions) and make a point of
    moveMatrix which is one grid point showing maximum direction at that grid point
    '''
    actionAbbr = ['U','D','L','R']
    movementGrid = []

    for i in range(row_max+1):
        #x = q_matrix[i*5 : i*5+5].flatten()
        x = q_matrix[i*num_rows : i*num_rows+num_cols].flatten()
        row = []
        for j in range(col_max+1):
            singleState = x[j*4 : j*4+4]
            qMax = np.max(singleState)
            indices = np.argwhere(singleState == qMax)
            row.append(actionAbbr[np.random.choice(indices.flatten())])
            #row.append(actionAbbr[np.argmax(x[j*4:j*4+4])])
        movementGrid.append(row)
    moveMatrix = np.array(movementGrid)
    
    #putting in pos and neg states
    moveMatrix[posState] = '+'
    moveMatrix[negState] = '-'
    
    return moveMatrix

def actionsAvailable(state, row_max, col_max):
    row, col = state
    directions = [-1,-1,-1,-1]
    if row < row_max: directions[1] = 0
    if row > 0: directions[0] = 0
    if col < col_max: directions[3] = 0
    if col > 0: directions[2] = 0
    return directions

def get_qMatrix_rowNum(state, col_max):
    return int((col_max + 1)*state[0] + state[1])

def neighbourStates(state, row_max, col_max):
    '''
    - Depending on 'state' we will get the one [above_it, below_it, left_of_it, on_its_right]
    - if no such state exists we will get -1
    - example:
      neighbourStates((0,0)) ==> [-1, (1, 0), -1, (0, 1)]
    '''
    neighbours = actionsAvailable(state, row_max, col_max)
    if neighbours[0] != -1:
        neighbours[0] = (state[0]-1, state[1])
    if neighbours[1] != -1:
        neighbours[1] = (state[0]+1, state[1])
    if neighbours[2] != -1:
        neighbours[2] = (state[0], state[1]-1)
    if neighbours[3] != -1:
        neighbours[3] = (state[0], state[1]+1)
    
    return neighbours

def update_qMatrix(state, q_matrix, row_max, col_max):
    q_temp = np.array(q_matrix, copy=True)
    actionIndex = [1,0,3,2]
    policeNeighbours = neighbourStates(state, row_max, col_max)
    for index, val in enumerate(policeNeighbours):
        if val != -1:
            q_matrix_row = get_qMatrix_rowNum(val, col_max)
            q_temp[q_matrix_row, actionIndex[index]] = np.min(q_temp)
            
    return q_temp

def createTrail(num_cols, posState, negState):
    '''
    aim: create a string matrix that shows the walls and pos/neg states
    '''
    emptyStrRow = [' ']*num_cols
    trailLst = []
    for _ in range(7):
        trailLst.append(emptyStrRow)
        
    trail = np.array(trailLst)
    trail[posState] = '+'
    trail[negState] = '-'
    return trail

def breadcrumb(state, policeState, q_matrix, row_max, col_max, num_rows, num_cols, posState, negState):
    '''
    aim: show the breadcrumb trail in matrix form of optimal path by car
    '''
    #state = (0,0)
    breadCrumb = [state]
    
    trail = createTrail(num_cols, posState, negState)
    trail[state] = '@'
    trail[policeState] = '#'
    
    new_q_matrix = update_qMatrix(policeState, q_matrix, row_max, col_max)
    
    while state != posState:
        direction = makeMoveMatrix(new_q_matrix, num_rows, num_cols, row_max, col_max, posState, negState)[state]
        if direction == 'U': state = (state[0]-1, state[1])
        if direction == 'D': state = (state[0]+1, state[1])
        if direction == 'L': state = (state[0], state[1]-1)
        if direction == 'R': state = (state[0], state[1]+1)
        
        breadCrumb.append(state)
    
    for element in breadCrumb[1:-1]:
        trail[element] = '*'
        
    return trail, breadCrumb

def createStates(num_rows, num_cols, posState, negState):
    '''
    aim: return the states that are available after discounting the
    pos, neg and wall states
    '''
    states = []

    for i in range(num_rows):
        for j in range(num_cols):
            states.append((i,j))

    availableState = states[:]
        
    availableState.pop(availableState.index(posState))
    availableState.pop(availableState.index(negState))

    return availableState

def gamePath(breadcrumb):
    '''
    Program return the game coordinates car should use to get to destination
    - breadcrumb: path as a list of states
    - Improvement: don't assume steps are always 100, use another variable to control this
    '''
    gamePath = []
    for state in breadcrumb:
        x_state, y_state = state
        x = y_state * 100
        y = x_state * 100
        gamePath.append((x,y))

    return gamePath

def getStateDirection(pathList, moveMatrix):
    angleList = []
    for path in pathList:
        direction = moveMatrix[path]
        if direction == 'U': angleList.append(90)
        if direction == 'D': angleList.append(270)
        if direction == 'L': angleList.append(180)
        if direction == 'R': angleList.append(0)

    # final reward should have car oriented right
    angleList.append(0)

    return angleList

def expandPath(gamePath):
    expandedPath = []
    count = 0
    while count < len(gamePath)-1:
        currentGridCoord = gamePath[count]
        expandedPath.append(currentGridCoord)
        
        delta_x = int((gamePath[count+1][0] - gamePath[count][0])/10)
        delta_y = int((gamePath[count+1][1] - gamePath[count][1])/10)

        x, y = currentGridCoord
        for _ in range(9):
            x = x + delta_x
            y = y + delta_y
            expandedPath.append( (x, y)  )
        count += 1
    expandedPath.append(gamePath[-1])
    return expandedPath

def expandAngle2(angleList):
    expandedAngle = []
    count = 0
    while count < len(angleList)-1:
        currentAngle = angleList[count]
        expandedAngle.append(currentAngle)

        angle = currentAngle

        first = angleList[count]
        last = angleList[count + 1]
        avg = 0.5*(first + last)
        #extra = [first, 0.75*first, 0.5*first, 0.25*first, avg, 0.25*last, 0.50*last, 0.75*last, last]
        extra = [first]*9
        expandedAngle.extend(extra)
    
        count += 1
    expandedAngle.append(angleList[-1])

    return expandedAngle        

def changeGame(carState, policeState):
    '''
    - everytime the police state changes update changeGame
    '''
    # define constants
    num_rows = 7 # total number of rows
    num_cols = 7 # total number of columns
    col_max = num_cols - 1 # index number start from 0 hence for say total row = 7, rows go from [0,6]
    row_max = num_rows - 1 # index number start from 0 hence for say total cols = 7, cols go from [0,6]

    # defining grid
    q_matrix, posState, negState = openPickledFiles()
    #updated_q_matrix = update_qMatrix(policeState, q_matrix, row_max, col_max)

    #moveMatrix = makeMoveMatrix(updated_q_matrix, num_rows, num_cols, row_max, col_max, posState, negState)
    #availableState = createStates(num_rows, num_cols, posState, negState)

    # trail shows the matrix string representation and breadcrumb is a list of tuples
    # each tuple is the state on path of destination
    
    #trail, path = breadcrumb(q_matrix, row_max, col_max, num_rows, num_cols, posState, negState)
    trail, path = breadcrumb(carState, policeState, q_matrix, row_max, col_max, num_rows, num_cols, posState, negState)

    # here we determine direction of car
    #angleList = getStateDirection(path, moveMatrix)

    # this path in grid coordinates
    game_path = gamePath(path)

    # intermediate states
    #expandedGamePath = expandPath(game_path)

    # intermediate angles
    #expandedAngle = expandAngle2(angleList)
    
    #return updated_q_matrix, game_path, trail, path, angleList, expandedGamePath, expandedAngle
    return game_path, trail
 
def playGame(game_path, policeState):
    # initialize
    pygame.init()

    display_width = 700
    display_height = 700

    black = (0,0,0)
    white = (255,255,255)
    red = (230,50,50)
    grey = (200,200,200)

    up_angle = 90
    right_angle = 0
    left_angle = 180
    down_angle = 270

    # tuple is width,height
    gameDisplay = pygame.display.set_mode((display_width,display_height))
    pygame.display.set_caption('Smart Car')

    clock = pygame.time.Clock()

    carImage = pygame.image.load('images/car-red.png')
    carImage = pygame.transform.scale(carImage, (90, 90))

    policeImage = pygame.image.load('images/car-black.png')
    policeImage = pygame.transform.scale(policeImage, (90, 90))

    moneybag = pygame.image.load('images/money_bag.jpg')
    moneybag = pygame.transform.scale(moneybag, (100, 100))
    
    jailHouse = pygame.image.load('images/jailHouse.png')
    jailHouse = pygame.transform.scale(jailHouse, (100, 100))

    carFootPath = pygame.image.load('images/car-white.png')
    carFootPath = pygame.transform.scale(carFootPath, (50,50))

    def car(x, y, angle):
        carImageRotated = pygame.transform.rotate(carImage, angle)
        gameDisplay.blit(carImageRotated,(x,y))

    def police(policeState, angle):
        policeImageRotated = pygame.transform.rotate(policeImage, angle)
        gameDisplay.blit(policeImageRotated, (policeState[1]*100, policeState[0]*100))

    def draw_moneyBag_jailHouse(x,y):
        gameDisplay.blit(moneybag,(x,y))
        gameDisplay.blit(jailHouse,(x-100,y-100))

    # ****
    def convertToGrid(x,y):
        return (int(y/100), int(x/100))

    def checkCarAndPoliceState(carState, policeState):
        if (policeState[0]-1 > 0) and (policeState[0]+1 < 6):
            return (carState[0]-1, carState[1])
        else:
            return (carState[0]+1, carState[1]) 
    # ****

    def game_loop(game_path, policeState):

        counter = 0
        n = 14

        carState = (0,0)

        gameExit = False

        while not gameExit:

            # we put all events in this loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    gameExit = True
                    pygame.quit()
                    quit()
            
            # regarding key being pressed
            pressed = pygame.key.get_pressed()
            if pressed[pygame.K_UP] and (policeState[0]*100>= 100):
                policeState = (policeState[0]-1, policeState[1])
                # ****
                #carState = checkCarAndPoliceState(carState, policeState)
                # ****
                game_path, _ = changeGame(carState, policeState)
                counter = 0
            if pressed[pygame.K_DOWN] and (policeState[0]*100<=500):
                policeState = (policeState[0]+1, policeState[1])
                # ****
                #carState = checkCarAndPoliceState(carState, policeState)
                # ****
                game_path, _ = changeGame(carState, policeState)
                counter = 0
            if pressed[pygame.K_LEFT] and (policeState[1]*100>= 100):
                policeState = (policeState[0], policeState[1]-1)
                # ****
                #carState = checkCarAndPoliceState(carState, policeState)
                # ****
                game_path, _ = changeGame(carState, policeState)
                counter = 0
            if pressed[pygame.K_RIGHT] and (policeState[1]*100<= 500):
                policeState = (policeState[0], policeState[1]+1)
                # ****
                #carState = checkCarAndPoliceState(carState, policeState)
                # ****
                game_path, _ = changeGame(carState, policeState)
                counter = 0                
            
            gameDisplay.fill(white)

            draw_moneyBag_jailHouse(600,600)
            police(policeState, 0)
            if counter < len(game_path):
                x,y = game_path[counter]
                # **** this is the section where we convert this to grid coordinates
                carState = convertToGrid(x,y)
                # ****
                angle = 0
                car(x,y,angle)
                print(len(game_path))
                counter += 1
            else:
                counter = 0
                carState = (0,0)
            
            pygame.display.update()
            clock.tick(n) 

    game_loop(game_path, policeState)
    pygame.quit()  # quit pygame
    quit()         # quit idle

if __name__ == '__main__':

    carState = (0,0)
    policeState = (6,0)
    game_path, trail = changeGame(carState, policeState)
    #print(game_path)

    playGame(game_path, policeState)


    
