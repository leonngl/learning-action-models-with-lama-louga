import sys

if __name__ == "__main__":
    filepath = sys.argv[1]

content = []
with open(filepath, "r") as f:
    for line in f:
         line = line.replace("pick_up", "pick-up")
         line = line.replace("put_down", "put-down")
         content.append(line.lstrip("1234567890: "))



with open(filepath, "w") as f:
      f.write("".join(content))

