def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def quick_sort(arr):
    """
    快速排序算法
    :param arr: 待排序的列表
    :return: 排序后的列表
    """
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quick_sort(left) + middle + quick_sort(right)


# 示例
if __name__ == "__main__":
    data = [64, 34, 25, 12, 22, 11, 90]
    print("排序前:", data)
    bubble_sort(data)
    print("排序后:", data)

    # 测试用例1：已排序数组（最好情况）
    data1 = [1, 2, 3, 4, 5]
    print("\n测试1 排序前:", data1)
    bubble_sort(data1)
    print("测试1 排序后:", data1)

    # 测试用例2：逆序数组（最坏情况）
    data2 = [5, 4, 3, 2, 1]
    print("\n测试2 排序前:", data2)
    bubble_sort(data2)
    print("测试2 排序后:", data2)

    # 测试用例3：含重复元素的数组
    data3 = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]
    print("\n测试3 排序前:", data3)
    bubble_sort(data3)
    print("测试3 排序后:", data3)
