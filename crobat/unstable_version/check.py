from matplotlib import pyplot as plt

day = 0
principal = 36000
interest_rate = 0.0715
pmt = 245
ttm_est = 15*24

xs = []
ys = []

for i in range(1,1000000000):
    principal *= (1+(interest_rate/24))
    if i%2 == 0:
        principal -= pmt 
    if principal < 0:
        break
    print(principal, "current run month",i) 
    xs.append(i)
    ys.append(principal)

plt.scatter(xs, ys)
plt.show()